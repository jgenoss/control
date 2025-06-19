"""
Configuración de la aplicación Flask
Maneja diferentes entornos: desarrollo, producción, testing
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    """Configuración base"""
    
    # Seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Base de datos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Cache
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hora
    
    # Tasas de cambio
    EXCHANGE_RATE_CACHE_TIMEOUT = 3600  # 1 hora
    EXCHANGE_RATE_SOURCES = {
        'FIXER_API_KEY': os.environ.get('FIXER_API_KEY'),
        'EXCHANGERATE_API_KEY': os.environ.get('EXCHANGERATE_API_KEY'),
        'FALLBACK_TO_XE': True
    }
    
    # Configuración de la aplicación
    ITEMS_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Configuración de sesiones
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuración de logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # Monedas soportadas
    SUPPORTED_CURRENCIES = ['COP', 'USD', 'EUR']
    DEFAULT_INCOME_CURRENCY = 'COP'
    DEFAULT_EXPENSE_CURRENCY = 'USD'


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///financial_app_dev.db'
    
    # Cache simple para desarrollo
    CACHE_TYPE = 'simple'
    
    # Logging más verboso
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Configuración para testing"""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///financial_app_test.db'
    
    # Desactivar CSRF para tests
    WTF_CSRF_ENABLED = False
    
    # Cache en memoria para tests
    CACHE_TYPE = 'simple'
    
    # Tasas de cambio fijas para tests
    EXCHANGE_RATE_SOURCES = {
        'FIXER_API_KEY': None,
        'EXCHANGERATE_API_KEY': None,
        'FALLBACK_TO_XE': False,
        'TEST_MODE': True,
        'TEST_RATES': {
            'USD_COP': 4100.00,
            'COP_USD': 0.000244
        }
    }


class ProductionConfig(Config):
    """Configuración para producción"""
    
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///financial_app.db'
    
    # Seguridad mejorada para producción
    SESSION_COOKIE_SECURE = True
    
    # Configuración de cache robusta
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    if not CACHE_REDIS_URL:
        CACHE_TYPE = 'filesystem'
        CACHE_DIR = '/tmp'
    
    # Logging estructurado
    LOG_TO_STDOUT = True


# Configuraciones disponibles
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """
    Obtiene la configuración basada en la variable de entorno FLASK_ENV
    """
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])


# Configuración de las categorías de gastos
EXPENSE_CATEGORIES = {
    'alimentacion': {'name': 'Alimentación', 'icon': '🍽️', 'color': '#FF6B6B'},
    'transporte': {'name': 'Transporte', 'icon': '🚗', 'color': '#4ECDC4'},
    'vivienda': {'name': 'Vivienda', 'icon': '🏠', 'color': '#45B7D1'},
    'servicios': {'name': 'Servicios Públicos', 'icon': '⚡', 'color': '#96CEB4'},
    'salud': {'name': 'Salud', 'icon': '🏥', 'color': '#FFEAA7'},
    'entretenimiento': {'name': 'Entretenimiento', 'icon': '🎮', 'color': '#DDA0DD'},
    'ropa': {'name': 'Ropa', 'icon': '👕', 'color': '#98D8C8'},
    'educacion': {'name': 'Educación', 'icon': '📚', 'color': '#F7DC6F'},
    'tecnologia': {'name': 'Tecnología', 'icon': '💻', 'color': '#BB8FCE'},
    'otros': {'name': 'Otros', 'icon': '📦', 'color': '#85C1E9'}
}

# Configuración de tipos de ingreso
INCOME_TYPES = {
    'salario': {'name': 'Salario', 'icon': '💼', 'color': '#2ECC71'},
    'freelance': {'name': 'Freelance', 'icon': '💻', 'color': '#3498DB'},
    'negocio': {'name': 'Negocio', 'icon': '🏢', 'color': '#E67E22'},
    'inversion': {'name': 'Inversiones', 'icon': '📈', 'color': '#9B59B6'},
    'venta': {'name': 'Ventas', 'icon': '🛒', 'color': '#1ABC9C'},
    'regalo': {'name': 'Regalos', 'icon': '🎁', 'color': '#E74C3C'},
    'otros': {'name': 'Otros', 'icon': '💰', 'color': '#F39C12'}
}