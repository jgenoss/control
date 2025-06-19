"""
Servicio de tasas de cambio con múltiples fuentes
Implementa web scraping de XE.com y APIs de respaldo
"""

import requests
import logging
import time
import random
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from flask import current_app, g
from models.models import db, ExchangeRate

logger = logging.getLogger(__name__)


class ExchangeRateError(Exception):
    """Excepción base para errores de tasas de cambio"""
    pass


class NoExchangeRateFound(ExchangeRateError):
    """No se pudo obtener la tasa de cambio de ninguna fuente"""
    pass


class ExchangeRateService:
    """
    Servicio para obtener tasas de cambio de múltiples fuentes
    Prioriza APIs oficiales y usa XE.com como último recurso
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Configurar timeout y reintentos
        self.session.timeout = 10
        
        # Fuentes de datos en orden de prioridad
        self.sources = [
            self._get_rate_from_fixer,
            self._get_rate_from_exchangerate_api,
            self._get_rate_from_ecb,
            self._get_rate_from_xe_scraping,
        ]
    
    def get_exchange_rate(self, from_currency: str, to_currency: str, 
                         use_cache: bool = True, force_update: bool = False) -> Decimal:
        """
        Obtiene la tasa de cambio entre dos monedas
        
        Args:
            from_currency: Moneda origen (ej: 'USD')
            to_currency: Moneda destino (ej: 'COP')
            use_cache: Si usar cache de base de datos
            force_update: Forzar actualización ignorando cache
        
        Returns:
            Decimal: Tasa de cambio
        
        Raises:
            NoExchangeRateFound: Si no se puede obtener la tasa
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Si las monedas son iguales, retorna 1
        if from_currency == to_currency:
            return Decimal('1.0')
        
        # Verificar cache si está habilitado
        if use_cache and not force_update:
            cached_rate = self._get_cached_rate(from_currency, to_currency)
            if cached_rate:
                logger.info(f"Usando tasa cached para {from_currency}/{to_currency}: {cached_rate}")
                return cached_rate
        
        # Intentar obtener de fuentes externas
        rate = self._fetch_rate_from_sources(from_currency, to_currency)
        
        if rate:
            # Guardar en cache
            self._save_rate_to_cache(from_currency, to_currency, rate, 'multi-source')
            return rate
        
        # Si no se pudo obtener, intentar usar cache expirado
        cached_rate = self._get_cached_rate(from_currency, to_currency, allow_expired=True)
        if cached_rate:
            logger.warning(f"Usando tasa expirada para {from_currency}/{to_currency}: {cached_rate}")
            return cached_rate
        
        raise NoExchangeRateFound(f"No se pudo obtener tasa de cambio para {from_currency}/{to_currency}")
    
    def _get_cached_rate(self, from_currency: str, to_currency: str, 
                        allow_expired: bool = False) -> Optional[Decimal]:
        """Obtiene tasa de cambio del cache (base de datos)"""
        
        # Calcular fecha límite para cache válido
        cache_hours = current_app.config.get('EXCHANGE_RATE_CACHE_TIMEOUT', 3600) // 3600
        cutoff_date = datetime.now().date() - timedelta(hours=cache_hours)
        
        query = ExchangeRate.query.filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
            ExchangeRate.is_active == True
        )
        
        if not allow_expired:
            query = query.filter(ExchangeRate.date >= cutoff_date)
        
        rate_record = query.order_by(ExchangeRate.date.desc(), ExchangeRate.created_at.desc()).first()
        
        if rate_record:
            return Decimal(str(rate_record.rate))
        
        return None
    
    def _save_rate_to_cache(self, from_currency: str, to_currency: str, 
                           rate: Decimal, source: str):
        """Guarda tasa de cambio en cache"""
        try:
            rate_record = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source=source,
                date=date.today()
            )
            db.session.add(rate_record)
            db.session.commit()
            logger.info(f"Tasa guardada en cache: {from_currency}/{to_currency} = {rate}")
        except Exception as e:
            logger.error(f"Error guardando tasa en cache: {e}")
            db.session.rollback()
    
    def _fetch_rate_from_sources(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Intenta obtener tasa de todas las fuentes disponibles"""
        
        for source_func in self.sources:
            try:
                rate = source_func(from_currency, to_currency)
                if rate and rate > 0:
                    logger.info(f"Tasa obtenida de {source_func.__name__}: {from_currency}/{to_currency} = {rate}")
                    return Decimal(str(rate))
            except Exception as e:
                logger.warning(f"Error en {source_func.__name__}: {e}")
                continue
        
        return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _get_rate_from_fixer(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Obtiene tasa de Fixer.io API"""
        
        api_key = current_app.config.get('EXCHANGE_RATE_SOURCES', {}).get('FIXER_API_KEY')
        if not api_key:
            logger.debug("API key de Fixer.io no configurada")
            return None
        
        url = f"http://data.fixer.io/api/latest"
        params = {
            'access_key': api_key,
            'base': from_currency,
            'symbols': to_currency
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success') and 'rates' in data:
            rate = data['rates'].get(to_currency)
            if rate:
                return float(rate)
        
        logger.warning(f"Fixer.io no devolvió tasa válida: {data}")
        return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _get_rate_from_exchangerate_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Obtiene tasa de ExchangeRates-API"""
        
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        if 'rates' in data:
            rate = data['rates'].get(to_currency)
            if rate:
                return float(rate)
        
        return None
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=5, max=15))
    def _get_rate_from_ecb(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Obtiene tasa del Banco Central Europeo (solo EUR)"""
        
        if from_currency != 'EUR' and to_currency != 'EUR':
            return None  # ECB solo proporciona tasas con EUR
        
        url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        
        response = self.session.get(url)
        response.raise_for_status()
        
        # Parsear XML del ECB
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        
        rates = {}
        for cube in root.findall(".//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@currency]"):
            currency = cube.get('currency')
            rate = float(cube.get('rate'))
            rates[currency] = rate
        
        if from_currency == 'EUR' and to_currency in rates:
            return rates[to_currency]
        elif to_currency == 'EUR' and from_currency in rates:
            return 1.0 / rates[from_currency]
        
        return None
    
    def _get_rate_from_xe_scraping(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Obtiene tasa de XE.com mediante web scraping
        Implementa múltiples métodos: requests + BeautifulSoup y Selenium
        """
        
        if not current_app.config.get('EXCHANGE_RATE_SOURCES', {}).get('FALLBACK_TO_XE', True):
            logger.debug("Web scraping de XE.com deshabilitado")
            return None
        
        # Intentar primero con requests + BeautifulSoup (más rápido)
        rate = self._scrape_xe_with_requests(from_currency, to_currency)
        if rate:
            return rate
        
        # Si falla, intentar con Selenium (más robusto)
        return self._scrape_xe_with_selenium(from_currency, to_currency)
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=4, max=10))
    def _scrape_xe_with_requests(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Scraping de XE.com usando requests + BeautifulSoup"""
        
        url = f"https://www.xe.com/es/currencyconverter/convert/?Amount=1&From={from_currency}&To={to_currency}"
        
        # Headers para simular navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Delay aleatorio para parecer más humano
        time.sleep(random.uniform(1, 3))
        
        response = self.session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Buscar el elemento que contiene la tasa de cambio
        # XE.com usa diferentes selectores, intentamos varios
        selectors = [
            'span.converterresult-ToAmount',
            '.converterresult-ToAmount',
            '[data-testid="converter-result-to-amount"]',
            '.result__BigRate',
            '.converterresult-toAmount'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                # Extraer número de la tasa
                rate = self._extract_rate_from_text(text)
                if rate:
                    logger.info(f"Tasa extraída de XE.com: {rate}")
                    return rate
        
        logger.warning("No se pudo extraer tasa de XE.com con requests")
        return None
    
    def _scrape_xe_with_selenium(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Scraping de XE.com usando Selenium (fallback robusto)"""
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(20)
            
            url = f"https://www.xe.com/es/currencyconverter/convert/?Amount=1&From={from_currency}&To={to_currency}"
            driver.get(url)
            
            # Esperar a que cargue el resultado
            wait = WebDriverWait(driver, 15)
            
            # Múltiples selectores para buscar el resultado
            selectors = [
                '[data-testid="converter-result-to-amount"]',
                '.converterresult-ToAmount',
                '.result__BigRate',
                '.converterresult-toAmount'
            ]
            
            for selector in selectors:
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    text = element.text.strip()
                    rate = self._extract_rate_from_text(text)
                    if rate:
                        logger.info(f"Tasa extraída de XE.com con Selenium: {rate}")
                        return rate
                except TimeoutException:
                    continue
            
            logger.warning("No se pudo extraer tasa de XE.com con Selenium")
            return None
            
        except (WebDriverException, TimeoutException) as e:
            logger.error(f"Error en Selenium: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _extract_rate_from_text(self, text: str) -> Optional[float]:
        """Extrae el número de la tasa de cambio del texto"""
        import re
        
        # Limpiar el texto
        text = text.replace(',', '').replace(' ', '')
        
        # Buscar patrones de números decimales
        patterns = [
            r'(\d+\.?\d*)',  # Números con o sin decimales
            r'(\d+,\d+)',    # Números con coma decimal (formato europeo)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Convertir coma decimal a punto
                    rate_str = match.group(1).replace(',', '.')
                    rate = float(rate_str)
                    if 0.0001 < rate < 1000000:  # Validar rango razonable
                        return rate
                except (ValueError, InvalidOperation):
                    continue
        
        return None
    
    def convert_amount(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """
        Convierte un monto de una moneda a otra
        
        Args:
            amount: Monto a convertir
            from_currency: Moneda origen
            to_currency: Moneda destino
        
        Returns:
            Decimal: Monto convertido
        """
        if from_currency == to_currency:
            return amount
        
        rate = self.get_exchange_rate(from_currency, to_currency)
        return amount * rate
    
    def get_supported_currencies(self) -> List[str]:
        """Devuelve lista de monedas soportadas"""
        return current_app.config.get('SUPPORTED_CURRENCIES', ['USD', 'COP', 'EUR'])
    
    def update_all_rates(self) -> Dict[str, bool]:
        """
        Actualiza todas las tasas de cambio soportadas
        Útil para tareas programadas
        """
        currencies = self.get_supported_currencies()
        results = {}
        
        for from_curr in currencies:
            for to_curr in currencies:
                if from_curr != to_curr:
                    try:
                        rate = self.get_exchange_rate(from_curr, to_curr, use_cache=False, force_update=True)
                        results[f"{from_curr}_{to_curr}"] = True
                        logger.info(f"Actualizada tasa {from_curr}/{to_curr}: {rate}")
                    except Exception as e:
                        results[f"{from_curr}_{to_curr}"] = False
                        logger.error(f"Error actualizando {from_curr}/{to_curr}: {e}")
        
        return results
    
    def __del__(self):
        """Cleanup del session"""
        if hasattr(self, 'session'):
            self.session.close()


# Instancia global del servicio
exchange_service = ExchangeRateService()


def get_exchange_service() -> ExchangeRateService:
    """
    Factory function para obtener el servicio de exchange
    Permite fácil testing e inyección de dependencias
    """
    if 'exchange_service' not in g:
        g.exchange_service = ExchangeRateService()
    return g.exchange_service