"""
Servicio de transacciones financieras
Maneja toda la lógica de negocio relacionada con ingresos y gastos
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func, extract
from flask import current_app

from models.models import db, Transaction, Account, ExchangeRate, Budget
from services.exchange_service import get_exchange_service, ExchangeRateError
from config import EXPENSE_CATEGORIES, INCOME_TYPES

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """Excepción base para errores de transacciones"""
    pass


class InsufficientFundsError(TransactionError):
    """Error cuando no hay fondos suficientes"""
    pass


class InvalidCurrencyError(TransactionError):
    """Error cuando la moneda no es válida"""
    pass


class TransactionService:
    """
    Servicio para gestionar transacciones financieras
    Incluye conversiones automáticas y validaciones de negocio
    """
    
    def __init__(self):
        self.exchange_service = get_exchange_service()
        self.supported_currencies = current_app.config.get('SUPPORTED_CURRENCIES', ['USD', 'COP', 'EUR'])
    
    def create_income(self, amount: Decimal, currency: str, description: str, 
                     category: str = 'otros', transaction_date: date = None,
                     account_id: int = None, notes: str = None, 
                     tags: List[str] = None) -> Transaction:
        """
        Crea una transacción de ingreso
        
        Args:
            amount: Monto del ingreso (positivo)
            currency: Moneda del ingreso
            description: Descripción del ingreso
            category: Categoría del ingreso
            transaction_date: Fecha de la transacción
            account_id: ID de la cuenta (opcional)
            notes: Notas adicionales
            tags: Lista de tags
        
        Returns:
            Transaction: Transacción creada
        """
        if amount <= 0:
            raise TransactionError("El monto del ingreso debe ser positivo")
        
        if currency not in self.supported_currencies:
            raise InvalidCurrencyError(f"Moneda {currency} no soportada")
        
        if not transaction_date:
            transaction_date = date.today()
        
        # Obtener cuenta por defecto si no se especifica
        if not account_id:
            account = self._get_default_income_account(currency)
            account_id = account.id
        
        # Crear la transacción
        transaction = Transaction(
            transaction_date=transaction_date,
            description=description,
            category=category,
            amount=amount,  # Positivo para ingresos
            currency=currency,
            transaction_type='income',
            account_id=account_id,
            notes=notes
        )
        
        if tags:
            transaction.tags_list = tags
        
        # Convertir a USD si la moneda es diferente
        if currency != 'USD':
            try:
                exchange_rate = self.exchange_service.get_exchange_rate(currency, 'USD')
                transaction.amount_usd = amount * exchange_rate
                
                # Guardar referencia a la tasa de cambio usada
                rate_record = self._get_or_create_exchange_rate_record(currency, 'USD', exchange_rate)
                transaction.exchange_rate_id = rate_record.id
                
            except ExchangeRateError as e:
                logger.warning(f"No se pudo convertir {currency} a USD: {e}")
                # Continuar sin conversión USD
        
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"Ingreso creado: {amount} {currency} - {description}")
        return transaction
    
    def create_expense(self, amount: Decimal, currency: str, description: str,
                      category: str, transaction_date: date = None,
                      account_id: int = None, notes: str = None,
                      tags: List[str] = None, subcategory: str = None) -> Transaction:
        """
        Crea una transacción de gasto
        
        Args:
            amount: Monto del gasto (positivo, se convertirá a negativo)
            currency: Moneda del gasto
            description: Descripción del gasto
            category: Categoría del gasto
            transaction_date: Fecha de la transacción
            account_id: ID de la cuenta (opcional)
            notes: Notas adicionales
            tags: Lista de tags
            subcategory: Subcategoría del gasto
        
        Returns:
            Transaction: Transacción creada
        """
        if amount <= 0:
            raise TransactionError("El monto del gasto debe ser positivo")
        
        if currency not in self.supported_currencies:
            raise InvalidCurrencyError(f"Moneda {currency} no soportada")
        
        if category not in EXPENSE_CATEGORIES:
            raise TransactionError(f"Categoría de gasto '{category}' no válida")
        
        if not transaction_date:
            transaction_date = date.today()
        
        # Obtener cuenta por defecto si no se especifica
        if not account_id:
            account = self._get_default_expense_account(currency)
            account_id = account.id
        
        # Crear la transacción (monto negativo para gastos)
        transaction = Transaction(
            transaction_date=transaction_date,
            description=description,
            category=category,
            subcategory=subcategory,
            amount=-amount,  # Negativo para gastos
            currency=currency,
            transaction_type='expense',
            account_id=account_id,
            notes=notes
        )
        
        if tags:
            transaction.tags_list = tags
        
        # Convertir a USD si la moneda es diferente
        if currency != 'USD':
            try:
                exchange_rate = self.exchange_service.get_exchange_rate(currency, 'USD')
                transaction.amount_usd = -amount * exchange_rate  # Negativo para gastos
                
                # Guardar referencia a la tasa de cambio usada
                rate_record = self._get_or_create_exchange_rate_record(currency, 'USD', exchange_rate)
                transaction.exchange_rate_id = rate_record.id
                
            except ExchangeRateError as e:
                logger.warning(f"No se pudo convertir {currency} a USD: {e}")
                # Continuar sin conversión USD
        
        # Verificar presupuestos
        budget_warning = self._check_budget_limits(category, amount, currency, transaction_date)
        if budget_warning:
            logger.warning(budget_warning)
        
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"Gasto creado: {amount} {currency} - {description}")
        return transaction
    
    def update_transaction(self, transaction_id: int, **kwargs) -> Transaction:
        """
        Actualiza una transacción existente
        
        Args:
            transaction_id: ID de la transacción
            **kwargs: Campos a actualizar
        
        Returns:
            Transaction: Transacción actualizada
        """
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            raise TransactionError(f"Transacción {transaction_id} no encontrada")
        
        # Campos que se pueden actualizar
        updateable_fields = [
            'description', 'category', 'subcategory', 'notes', 
            'transaction_date', 'amount', 'currency'
        ]
        
        amount_changed = 'amount' in kwargs
        currency_changed = 'currency' in kwargs
        
        # Actualizar campos
        for field, value in kwargs.items():
            if field in updateable_fields:
                if field == 'amount':
                    # Validar signo según tipo de transacción
                    if transaction.transaction_type == 'income' and value <= 0:
                        raise TransactionError("El monto de ingreso debe ser positivo")
                    elif transaction.transaction_type == 'expense' and value >= 0:
                        raise TransactionError("El monto de gasto debe ser negativo")
                
                setattr(transaction, field, value)
        
        # Recalcular conversión USD si cambió monto o moneda
        if (amount_changed or currency_changed) and transaction.currency != 'USD':
            try:
                exchange_rate = self.exchange_service.get_exchange_rate(transaction.currency, 'USD')
                transaction.amount_usd = transaction.amount * exchange_rate
                
                # Actualizar referencia a tasa de cambio
                rate_record = self._get_or_create_exchange_rate_record(
                    transaction.currency, 'USD', exchange_rate
                )
                transaction.exchange_rate_id = rate_record.id
                
            except ExchangeRateError as e:
                logger.warning(f"No se pudo actualizar conversión USD: {e}")
        
        db.session.commit()
        
        logger.info(f"Transacción {transaction_id} actualizada")
        return transaction
    
    def delete_transaction(self, transaction_id: int, soft_delete: bool = True) -> bool:
        """
        Elimina una transacción
        
        Args:
            transaction_id: ID de la transacción
            soft_delete: Si hacer eliminación suave (marcar como inactiva)
        
        Returns:
            bool: True si se eliminó correctamente
        """
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            raise TransactionError(f"Transacción {transaction_id} no encontrada")
        
        if soft_delete:
            transaction.is_active = False
            logger.info(f"Transacción {transaction_id} marcada como inactiva")
        else:
            db.session.delete(transaction)
            logger.info(f"Transacción {transaction_id} eliminada permanentemente")
        
        db.session.commit()
        return True
    
    def get_transactions(self, start_date: date = None, end_date: date = None,
                        category: str = None, transaction_type: str = None,
                        account_id: int = None, limit: int = None,
                        offset: int = 0, include_inactive: bool = False) -> List[Transaction]:
        """
        Obtiene transacciones con filtros
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            category: Filtrar por categoría
            transaction_type: 'income' o 'expense'
            account_id: ID de cuenta específica
            limit: Límite de resultados
            offset: Offset para paginación
            include_inactive: Incluir transacciones inactivas
        
        Returns:
            List[Transaction]: Lista de transacciones
        """
        query = Transaction.query
        
        if not include_inactive:
            query = query.filter(Transaction.is_active == True)
        
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        
        if category:
            query = query.filter(Transaction.category == category)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        
        # Ordenar por fecha descendente
        query = query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        if offset:
            query = query.offset(offset)
        
        return query.all()
    
    def get_balance_summary(self, currency: str = 'USD', as_of_date: date = None) -> Dict:
        """
        Obtiene resumen de balance en una moneda específica
        
        Args:
            currency: Moneda para el resumen
            as_of_date: Fecha hasta la cual calcular (None = hoy)
        
        Returns:
            Dict: Resumen con totales de ingresos, gastos y balance
        """
        if not as_of_date:
            as_of_date = date.today()
        
        query = Transaction.query.filter(
            Transaction.transaction_date <= as_of_date,
            Transaction.is_active == True
        )
        
        # Si es USD, usar los montos convertidos cuando estén disponibles
        if currency == 'USD':
            # Ingresos en USD
            income_usd = query.filter(
                Transaction.transaction_type == 'income',
                Transaction.amount_usd_cents.isnot(None)
            ).with_entities(func.sum(Transaction.amount_usd_cents)).scalar() or 0
            
            # Gastos en USD
            expense_usd = query.filter(
                Transaction.transaction_type == 'expense',
                Transaction.amount_usd_cents.isnot(None)
            ).with_entities(func.sum(Transaction.amount_usd_cents)).scalar() or 0
            
            # Transacciones directamente en USD
            income_direct = query.filter(
                Transaction.transaction_type == 'income',
                Transaction.currency == 'USD'
            ).with_entities(func.sum(Transaction.amount_cents)).scalar() or 0
            
            expense_direct = query.filter(
                Transaction.transaction_type == 'expense',
                Transaction.currency == 'USD'
            ).with_entities(func.sum(Transaction.amount_cents)).scalar() or 0
            
            # Combinar totales (evitar duplicar transacciones ya en USD)
            total_income = (income_usd + income_direct) / 100
            total_expense = abs((expense_usd + expense_direct) / 100)
            
        else:
            # Para otras monedas, filtrar por moneda específica
            income_total = query.filter(
                Transaction.transaction_type == 'income',
                Transaction.currency == currency
            ).with_entities(func.sum(Transaction.amount_cents)).scalar() or 0
            
            expense_total = query.filter(
                Transaction.transaction_type == 'expense',
                Transaction.currency == currency
            ).with_entities(func.sum(Transaction.amount_cents)).scalar() or 0
            
            total_income = Decimal(income_total) / 100
            total_expense = abs(Decimal(expense_total) / 100)
        
        balance = total_income - total_expense
        
        return {
            'currency': currency,
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'balance': float(balance),
            'as_of_date': as_of_date.isoformat()
        }
    
    def get_monthly_summary(self, year: int, month: int, currency: str = 'USD') -> Dict:
        """
        Obtiene resumen mensual de transacciones
        
        Args:
            year: Año
            month: Mes (1-12)
            currency: Moneda para el resumen
        
        Returns:
            Dict: Resumen mensual
        """
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        transactions = self.get_transactions(start_date=start_date, end_date=end_date)
        
        # Agrupar por categoría
        income_by_category = {}
        expense_by_category = {}
        
        for transaction in transactions:
            amount = self._convert_to_currency(transaction, currency)
            
            if transaction.transaction_type == 'income':
                category = transaction.category
                income_by_category[category] = income_by_category.get(category, 0) + abs(amount)
            else:
                category = transaction.category
                expense_by_category[category] = expense_by_category.get(category, 0) + abs(amount)
        
        total_income = sum(income_by_category.values())
        total_expense = sum(expense_by_category.values())
        
        return {
            'year': year,
            'month': month,
            'currency': currency,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'income_by_category': income_by_category,
            'expense_by_category': expense_by_category,
            'transaction_count': len(transactions)
        }
    
    def get_category_analysis(self, start_date: date = None, end_date: date = None,
                            currency: str = 'USD') -> Dict:
        """
        Analiza gastos por categoría en un período
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            currency: Moneda para el análisis
        
        Returns:
            Dict: Análisis por categorías
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        transactions = self.get_transactions(
            start_date=start_date, 
            end_date=end_date, 
            transaction_type='expense'
        )
        
        category_totals = {}
        category_counts = {}
        
        for transaction in transactions:
            amount = abs(self._convert_to_currency(transaction, currency))
            category = transaction.category
            
            category_totals[category] = category_totals.get(category, 0) + amount
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calcular porcentajes
        total_spending = sum(category_totals.values())
        category_analysis = {}
        
        for category, amount in category_totals.items():
            percentage = (amount / total_spending * 100) if total_spending > 0 else 0
            category_analysis[category] = {
                'amount': amount,
                'percentage': round(percentage, 2),
                'count': category_counts[category],
                'average': amount / category_counts[category],
                'category_info': EXPENSE_CATEGORIES.get(category, {'name': category, 'icon': '📊'})
            }
        
        # Ordenar por monto descendente
        sorted_categories = sorted(category_analysis.items(), key=lambda x: x[1]['amount'], reverse=True)
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'currency': currency,
            'total_spending': total_spending,
            'categories': dict(sorted_categories),
            'top_category': sorted_categories[0] if sorted_categories else None
        }
    
    def _get_default_income_account(self, currency: str) -> Account:
        """Obtiene cuenta por defecto para ingresos"""
        account = Account.query.filter(
            Account.account_type == 'income',
            Account.currency == currency,
            Account.is_active == True
        ).first()
        
        if not account:
            # Crear cuenta por defecto si no existe
            account = Account(
                name=f'Ingresos {currency}',
                account_type='income',
                currency=currency,
                description=f'Cuenta por defecto para ingresos en {currency}'
            )
            db.session.add(account)
            db.session.commit()
        
        return account
    
    def _get_default_expense_account(self, currency: str) -> Account:
        """Obtiene cuenta por defecto para gastos"""
        account = Account.query.filter(
            Account.account_type == 'expense',
            Account.currency == currency,
            Account.is_active == True
        ).first()
        
        if not account:
            # Crear cuenta por defecto si no existe
            account = Account(
                name=f'Gastos {currency}',
                account_type='expense',
                currency=currency,
                description=f'Cuenta por defecto para gastos en {currency}'
            )
            db.session.add(account)
            db.session.commit()
        
        return account
    
    def _get_or_create_exchange_rate_record(self, from_currency: str, 
                                          to_currency: str, rate: Decimal) -> ExchangeRate:
        """Obtiene o crea un registro de tasa de cambio"""
        # Buscar tasa existente para hoy
        today = date.today()
        existing_rate = ExchangeRate.query.filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
            ExchangeRate.date == today,
            ExchangeRate.is_active == True
        ).first()
        
        if existing_rate:
            return existing_rate
        
        # Crear nueva tasa
        rate_record = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            source='transaction_service',
            date=today
        )
        db.session.add(rate_record)
        db.session.flush()  # Para obtener el ID
        
        return rate_record
    
    def _convert_to_currency(self, transaction: Transaction, target_currency: str) -> Decimal:
        """Convierte el monto de una transacción a la moneda objetivo"""
        if transaction.currency == target_currency:
            return transaction.amount
        
        try:
            rate = self.exchange_service.get_exchange_rate(transaction.currency, target_currency)
            return transaction.amount * rate
        except ExchangeRateError:
            logger.warning(f"No se pudo convertir {transaction.currency} a {target_currency}")
            return transaction.amount  # Devolver monto original
    
    def _check_budget_limits(self, category: str, amount: Decimal, 
                           currency: str, transaction_date: date) -> Optional[str]:
        """Verifica si el gasto excede límites de presupuesto"""
        # Buscar presupuestos activos para la categoría que incluyan la fecha
        budgets = Budget.query.filter(
            Budget.category == category,
            Budget.start_date <= transaction_date,
            Budget.end_date >= transaction_date,
            Budget.is_active == True
        ).all()
        
        for budget in budgets:
            spent_amount = budget.get_spent_amount()
            if currency != budget.currency:
                # Convertir monto a moneda del presupuesto
                try:
                    rate = self.exchange_service.get_exchange_rate(currency, budget.currency)
                    converted_amount = amount * rate
                except ExchangeRateError:
                    continue  # Si no se puede convertir, omitir verificación
            else:
                converted_amount = amount
            
            new_total = spent_amount + converted_amount
            if new_total > budget.amount:
                return (f"Advertencia: Este gasto excederá el presupuesto '{budget.name}' "
                       f"({new_total}/{budget.amount} {budget.currency})")
            elif new_total > budget.amount * Decimal('0.8'):
                return (f"Advertencia: Has usado el {budget.percentage_used:.1f}% "
                       f"del presupuesto '{budget.name}'")
        
        return None


# Instancia global del servicio
transaction_service = TransactionService()


def get_transaction_service() -> TransactionService:
    """Factory function para obtener el servicio de transacciones"""
    return transaction_service