"""
Modelos de base de datos para la aplicación financiera
Implementa principios de contabilidad y integridad de datos
"""

from datetime import datetime, timezone
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index
from sqlalchemy.ext.hybrid import hybrid_property
import json

db = SQLAlchemy()


class TimestampMixin:
    """Mixin para timestamps automáticos"""
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ExchangeRate(db.Model, TimestampMixin):
    """
    Almacena tasas de cambio históricas
    Permite auditoría completa de conversiones
    """
    __tablename__ = 'exchange_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(precision=12, scale=6), nullable=False)
    source = db.Column(db.String(50), nullable=False)  # 'fixer', 'xe', 'ecb', etc.
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('rate > 0', name='check_positive_rate'),
        CheckConstraint('from_currency != to_currency', name='check_different_currencies'),
        Index('idx_exchange_rates_currencies_date', 'from_currency', 'to_currency', 'date'),
        Index('idx_exchange_rates_active', 'is_active', 'date'),
    )
    
    def __repr__(self):
        return f'<ExchangeRate {self.from_currency}/{self.to_currency}: {self.rate}>'
    
    @classmethod
    def get_latest_rate(cls, from_currency, to_currency):
        """Obtiene la tasa más reciente entre dos monedas"""
        return cls.query.filter(
            cls.from_currency == from_currency,
            cls.to_currency == to_currency,
            cls.is_active == True
        ).order_by(cls.date.desc(), cls.created_at.desc()).first()
    
    def to_dict(self):
        return {
            'id': self.id,
            'from_currency': self.from_currency,
            'to_currency': self.to_currency,
            'rate': float(self.rate),
            'source': self.source,
            'date': self.date.isoformat(),
            'created_at': self.created_at.isoformat()
        }


class Account(db.Model, TimestampMixin):
    """
    Cuentas para organizar transacciones
    Implementa estructura de contabilidad básica
    """
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # 'asset', 'liability', 'income', 'expense'
    currency = db.Column(db.String(3), nullable=False, default='USD')
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relaciones
    transactions = db.relationship('Transaction', backref='account', lazy='dynamic')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("account_type IN ('asset', 'liability', 'income', 'expense')", 
                       name='check_valid_account_type'),
    )
    
    def __repr__(self):
        return f'<Account {self.name} ({self.account_type})>'
    
    @hybrid_property
    def balance(self):
        """Calcula el balance actual de la cuenta"""
        total = db.session.query(db.func.sum(Transaction.amount_cents)).filter(
            Transaction.account_id == self.id,
            Transaction.is_active == True
        ).scalar() or 0
        return Decimal(total) / 100
    
    def balance_at_date(self, date):
        """Calcula el balance a una fecha específica"""
        total = db.session.query(db.func.sum(Transaction.amount_cents)).filter(
            Transaction.account_id == self.id,
            Transaction.transaction_date <= date,
            Transaction.is_active == True
        ).scalar() or 0
        return Decimal(total) / 100
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'account_type': self.account_type,
            'currency': self.currency,
            'balance': float(self.balance),
            'is_active': self.is_active
        }


class Transaction(db.Model, TimestampMixin):
    """
    Transacciones financieras individuales
    Almacena montos en centavos para evitar errores de precisión
    """
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50))
    
    # Montos en centavos para precisión
    amount_cents = db.Column(db.BigInteger, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    
    # Conversión a moneda base (USD)
    amount_usd_cents = db.Column(db.BigInteger)
    exchange_rate_id = db.Column(db.Integer, db.ForeignKey('exchange_rates.id'))
    
    # Tipo de transacción
    transaction_type = db.Column(db.String(10), nullable=False)  # 'income', 'expense'
    
    # Referencias
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    reference = db.Column(db.String(100))  # Número de factura, etc.
    
    # Metadatos
    tags = db.Column(db.Text)  # JSON array de tags
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relaciones
    exchange_rate = db.relationship('ExchangeRate', backref='transactions')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount_cents != 0', name='check_non_zero_amount'),
        CheckConstraint("transaction_type IN ('income', 'expense')", 
                       name='check_valid_transaction_type'),
        CheckConstraint("(transaction_type = 'income' AND amount_cents > 0) OR "
                       "(transaction_type = 'expense' AND amount_cents < 0)",
                       name='check_amount_sign_consistency'),
        Index('idx_transactions_date', 'transaction_date'),
        Index('idx_transactions_type_date', 'transaction_type', 'transaction_date'),
        Index('idx_transactions_category', 'category'),
        Index('idx_transactions_account_date', 'account_id', 'transaction_date'),
    )
    
    def __repr__(self):
        return f'<Transaction {self.description}: {self.amount_display} {self.currency}>'
    
    @hybrid_property
    def amount(self):
        """Convierte centavos a monto decimal"""
        return Decimal(self.amount_cents) / 100 if self.amount_cents else Decimal('0')
    
    @amount.setter
    def amount(self, value):
        """Convierte monto decimal a centavos"""
        if value is not None:
            self.amount_cents = int(Decimal(str(value)) * 100)
        else:
            self.amount_cents = 0
    
    @hybrid_property
    def amount_usd(self):
        """Convierte centavos USD a monto decimal"""
        return Decimal(self.amount_usd_cents) / 100 if self.amount_usd_cents else Decimal('0')
    
    @amount_usd.setter
    def amount_usd(self, value):
        """Convierte monto decimal USD a centavos"""
        if value is not None:
            self.amount_usd_cents = int(Decimal(str(value)) * 100)
        else:
            self.amount_usd_cents = 0
    
    @property
    def amount_display(self):
        """Formatea el monto para mostrar"""
        return abs(self.amount)
    
    @property
    def tags_list(self):
        """Devuelve los tags como lista"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except json.JSONDecodeError:
                return []
        return []
    
    @tags_list.setter
    def tags_list(self, value):
        """Guarda los tags como JSON"""
        if value:
            self.tags = json.dumps(value)
        else:
            self.tags = None
    
    def to_dict(self, include_usd=True):
        """Convierte la transacción a diccionario"""
        data = {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat(),
            'description': self.description,
            'category': self.category,
            'subcategory': self.subcategory,
            'amount': float(self.amount_display),
            'currency': self.currency,
            'transaction_type': self.transaction_type,
            'reference': self.reference,
            'tags': self.tags_list,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
        
        if include_usd and self.amount_usd_cents:
            data['amount_usd'] = float(self.amount_usd)
            data['exchange_rate'] = float(self.exchange_rate.rate) if self.exchange_rate else None
        
        return data
    
    @classmethod
    def get_monthly_summary(cls, year, month, transaction_type=None):
        """Obtiene resumen mensual de transacciones"""
        query = cls.query.filter(
            db.extract('year', cls.transaction_date) == year,
            db.extract('month', cls.transaction_date) == month,
            cls.is_active == True
        )
        
        if transaction_type:
            query = query.filter(cls.transaction_type == transaction_type)
        
        return query.all()
    
    @classmethod
    def get_category_summary(cls, start_date=None, end_date=None):
        """Obtiene resumen por categorías"""
        query = db.session.query(
            cls.category,
            db.func.sum(cls.amount_cents).label('total_cents'),
            db.func.count(cls.id).label('count')
        ).filter(cls.is_active == True)
        
        if start_date:
            query = query.filter(cls.transaction_date >= start_date)
        if end_date:
            query = query.filter(cls.transaction_date <= end_date)
        
        return query.group_by(cls.category).all()


class Budget(db.Model, TimestampMixin):
    """
    Presupuestos por categoría y período
    """
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount_cents = db.Column(db.BigInteger, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    
    # Período del presupuesto
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount_cents > 0', name='check_positive_budget'),
        CheckConstraint('end_date > start_date', name='check_valid_date_range'),
    )
    
    @hybrid_property
    def amount(self):
        """Convierte centavos a monto decimal"""
        return Decimal(self.amount_cents) / 100
    
    @amount.setter
    def amount(self, value):
        """Convierte monto decimal a centavos"""
        self.amount_cents = int(Decimal(str(value)) * 100)
    
    def get_spent_amount(self):
        """Calcula cuánto se ha gastado en este presupuesto"""
        total = db.session.query(db.func.sum(Transaction.amount_cents)).filter(
            Transaction.category == self.category,
            Transaction.transaction_date >= self.start_date,
            Transaction.transaction_date <= self.end_date,
            Transaction.transaction_type == 'expense',
            Transaction.is_active == True
        ).scalar() or 0
        
        return abs(Decimal(total) / 100)  # Valor absoluto porque los gastos son negativos
    
    @property
    def remaining_amount(self):
        """Calcula cuánto queda del presupuesto"""
        return self.amount - self.get_spent_amount()
    
    @property
    def percentage_used(self):
        """Calcula el porcentaje usado del presupuesto"""
        spent = self.get_spent_amount()
        if self.amount > 0:
            return float((spent / self.amount) * 100)
        return 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'amount': float(self.amount),
            'currency': self.currency,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'spent_amount': float(self.get_spent_amount()),
            'remaining_amount': float(self.remaining_amount),
            'percentage_used': self.percentage_used,
            'is_active': self.is_active
        }


# Eventos de SQLAlchemy para mantener integridad
from sqlalchemy import event

@event.listens_for(Transaction, 'before_insert')
@event.listens_for(Transaction, 'before_update')
def validate_transaction_amounts(mapper, connection, target):
    """Valida que los montos sean consistentes con el tipo de transacción"""
    if target.transaction_type == 'income' and target.amount_cents <= 0:
        raise ValueError("Los ingresos deben tener montos positivos")
    elif target.transaction_type == 'expense' and target.amount_cents >= 0:
        raise ValueError("Los gastos deben tener montos negativos")


def init_default_accounts(db):
    """Inicializa cuentas por defecto"""
    default_accounts = [
        Account(name='Efectivo COP', account_type='asset', currency='COP'),
        Account(name='Efectivo USD', account_type='asset', currency='USD'),
        Account(name='Ingresos COP', account_type='income', currency='COP'),
        Account(name='Gastos USD', account_type='expense', currency='USD'),
    ]
    
    for account in default_accounts:
        existing = Account.query.filter_by(name=account.name).first()
        if not existing:
            db.session.add(account)
    
    db.session.commit()