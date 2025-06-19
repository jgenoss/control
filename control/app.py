"""
Aplicación principal Flask para control de gastos personales
Implementa arquitectura de Application Factory con blueprints
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, jsonify
from flask_migrate import Migrate
from flask_caching import Cache
from flask_talisman import Talisman

# Importar configuración y modelos
from config import get_config
from models.models import db, init_default_accounts

# Cache global
cache = Cache()
migrate = Migrate()


def create_app(config_name=None):
    """
    Application Factory Pattern
    Crea y configura la aplicación Flask
    
    Args:
        config_name: Nombre de la configuración ('development', 'production', 'testing')
    
    Returns:
        Flask: Aplicación Flask configurada
    """
    app = Flask(__name__)
    
    # Cargar configuración
    if config_name:
        from config import config
        app.config.from_object(config[config_name])
    else:
        config_class = get_config()
        app.config.from_object(config_class)
    
    # Inicializar extensiones
    init_extensions(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Configurar logging
    configure_logging(app)
    
    # Manejadores de errores
    register_error_handlers(app)
    
    # Comandos CLI
    register_cli_commands(app)
    
    # Inicializar base de datos
    with app.app_context():
        init_database()
    
    return app


def init_extensions(app):
    """Inicializa todas las extensiones de Flask"""
    
    # Base de datos
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Cache
    cache.init_app(app)
    
    # Seguridad (solo en producción)
    if not app.config.get('DEBUG', False):
        Talisman(app, force_https=False)  # Cambiar a True en producción con HTTPS
    
    # Configurar filtros Jinja2 personalizados
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['percentage'] = format_percentage


def register_blueprints(app):
    """Registra todos los blueprints de la aplicación"""
    
    # Blueprint principal (dashboard, páginas principales)
    from routes.main import main_bp
    app.register_blueprint(main_bp)
    
    # Blueprint de transacciones
    from routes.transactions import transactions_bp
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    
    # Blueprint de API REST
    from routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')


def configure_logging(app):
    """Configura el sistema de logging"""
    
    if not app.debug and not app.testing:
        # Logging a archivo en producción
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/financial_app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Financial App startup')
    
    # Logging a stdout en desarrollo o si está configurado
    if app.config.get('LOG_TO_STDOUT'):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)


def register_error_handlers(app):
    """Registra manejadores de errores personalizados"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        if app.config.get('DEBUG'):
            return jsonify({'error': 'Página no encontrada'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Error interno del servidor: {error}')
        if app.config.get('DEBUG'):
            return jsonify({'error': 'Error interno del servidor'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403


def register_cli_commands(app):
    """Registra comandos CLI personalizados"""
    
    @app.cli.command()
    def init_db():
        """Inicializa la base de datos con datos por defecto"""
        db.create_all()
        init_default_accounts(db)
        print('Base de datos inicializada.')
    
    @app.cli.command()
    def update_rates():
        """Actualiza todas las tasas de cambio"""
        from services.exchange_service import get_exchange_service
        
        service = get_exchange_service()
        results = service.update_all_rates()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f'Tasas actualizadas: {success_count}/{total_count}')
        
        for pair, success in results.items():
            status = "✓" if success else "✗"
            print(f'{status} {pair}')
    
    @app.cli.command()
    def create_sample_data():
        """Crea datos de ejemplo para desarrollo"""
        from datetime import date, timedelta
        from services.transaction_service import get_transaction_service
        from decimal import Decimal
        import random
        
        service = get_transaction_service()
        
        # Crear algunos ingresos de ejemplo
        income_data = [
            (Decimal('2500000'), 'COP', 'Salario Diciembre', 'salario'),
            (Decimal('800000'), 'COP', 'Freelance desarrollo web', 'freelance'),
            (Decimal('300000'), 'COP', 'Venta de productos', 'venta'),
        ]
        
        for amount, currency, description, category in income_data:
            transaction_date = date.today() - timedelta(days=random.randint(1, 30))
            service.create_income(amount, currency, description, category, transaction_date)
        
        # Crear algunos gastos de ejemplo
        expense_data = [
            (Decimal('25.50'), 'USD', 'Almuerzo restaurante', 'alimentacion'),
            (Decimal('45.00'), 'USD', 'Supermercado semanal', 'alimentacion'),
            (Decimal('12.00'), 'USD', 'Transporte público', 'transporte'),
            (Decimal('80.00'), 'USD', 'Servicios de internet', 'servicios'),
            (Decimal('15.00'), 'USD', 'Suscripción Netflix', 'entretenimiento'),
            (Decimal('35.00'), 'USD', 'Medicamentos', 'salud'),
            (Decimal('60.00'), 'USD', 'Compra ropa', 'ropa'),
        ]
        
        for amount, currency, description, category in expense_data:
            transaction_date = date.today() - timedelta(days=random.randint(1, 30))
            service.create_expense(amount, currency, description, category, transaction_date)
        
        print('Datos de ejemplo creados.')
    
    @app.cli.command()
    def export_data():
        """Exporta datos a CSV"""
        import csv
        from models.models import Transaction
        
        transactions = Transaction.query.filter(Transaction.is_active == True).all()
        
        with open('transactions_export.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'fecha', 'tipo', 'categoria', 'descripcion', 
                'monto', 'moneda', 'monto_usd', 'notas'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for t in transactions:
                writer.writerow({
                    'fecha': t.transaction_date.isoformat(),
                    'tipo': t.transaction_type,
                    'categoria': t.category,
                    'descripcion': t.description,
                    'monto': float(t.amount_display),
                    'moneda': t.currency,
                    'monto_usd': float(t.amount_usd) if t.amount_usd else '',
                    'notas': t.notes or ''
                })
        
        print(f'Exportadas {len(transactions)} transacciones a transactions_export.csv')


def init_database():
    """Inicializa la base de datos si es necesario"""
    try:
        # Crear tablas si no existen
        db.create_all()
        
        # Inicializar cuentas por defecto
        init_default_accounts(db)
        
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")


# Filtros Jinja2 personalizados
def format_currency(amount, currency='USD'):
    """Formatea un monto como moneda"""
    if currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'COP':
        return f"${amount:,.0f} COP"
    else:
        return f"{amount:,.2f} {currency}"


def format_percentage(value, decimals=1):
    """Formatea un valor como porcentaje"""
    return f"{value:.{decimals}f}%"


# Contexto global para templates
@cache.memoize(timeout=300)  # Cache por 5 minutos
def get_expense_categories():
    """Obtiene categorías de gastos para templates"""
    from config import EXPENSE_CATEGORIES
    return EXPENSE_CATEGORIES


@cache.memoize(timeout=300)
def get_income_types():
    """Obtiene tipos de ingresos para templates"""
    from config import INCOME_TYPES
    return INCOME_TYPES


def register_template_globals(app):
    """Registra variables globales para templates"""
    
    @app.context_processor
    def inject_globals():
        return {
            'expense_categories': get_expense_categories(),
            'income_types': get_income_types(),
            'supported_currencies': app.config.get('SUPPORTED_CURRENCIES', ['USD', 'COP'])
        }


# Crear aplicación si se ejecuta directamente
if __name__ == '__main__':
    app = create_app()
    
    # Registrar variables globales para templates
    register_template_globals(app)
    
    # Configuración para desarrollo
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )