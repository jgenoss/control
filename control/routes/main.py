"""
Blueprint principal para rutas del dashboard y páginas principales
Maneja la interfaz web principal de la aplicación
"""

from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from sqlalchemy import func, extract
from decimal import Decimal

from models.models import db, Transaction, Account, ExchangeRate
from services.transaction_service import get_transaction_service
from services.exchange_service import get_exchange_service
from config import EXPENSE_CATEGORIES, INCOME_TYPES

# Crear blueprint
main_bp = Blueprint('main', __name__)

# Servicios
transaction_service = get_transaction_service()
exchange_service = get_exchange_service()


@main_bp.route('/')
def dashboard():
    """
    Dashboard principal con resumen financiero
    Muestra balance, gráficos y transacciones recientes
    """
    try:
        # Obtener fecha actual
        today = date.today()
        current_month = today.month
        current_year = today.year
        
        # Resumen de balance en USD
        balance_summary = transaction_service.get_balance_summary('USD', today)
        
        # Resumen mensual actual
        monthly_summary = transaction_service.get_monthly_summary(current_year, current_month, 'USD')
        
        # Transacciones recientes (últimas 10)
        recent_transactions = transaction_service.get_transactions(limit=10)
        
        # Análisis de categorías del mes actual
        start_of_month = date(current_year, current_month, 1)
        category_analysis = transaction_service.get_category_analysis(start_of_month, today, 'USD')
        
        # Obtener tasa de cambio actual USD/COP
        try:
            current_rate = exchange_service.get_exchange_rate('USD', 'COP')
            rate_info = {
                'rate': float(current_rate),
                'updated': datetime.now().strftime('%H:%M')
            }
        except Exception as e:
            rate_info = {
                'rate': 4100.0,  # Fallback
                'updated': 'Error',
                'error': str(e)
            }
        
        # Calcular tendencias (comparar con mes anterior)
        if current_month == 1:
            prev_month, prev_year = 12, current_year - 1
        else:
            prev_month, prev_year = current_month - 1, current_year
        
        prev_monthly_summary = transaction_service.get_monthly_summary(prev_year, prev_month, 'USD')
        
        # Calcular variaciones porcentuales
        income_trend = calculate_percentage_change(
            prev_monthly_summary['total_income'], 
            monthly_summary['total_income']
        )
        expense_trend = calculate_percentage_change(
            prev_monthly_summary['total_expense'], 
            monthly_summary['total_expense']
        )
        
        return render_template('dashboard.html',
                             balance_summary=balance_summary,
                             monthly_summary=monthly_summary,
                             recent_transactions=recent_transactions,
                             category_analysis=category_analysis,
                             rate_info=rate_info,
                             income_trend=income_trend,
                             expense_trend=expense_trend,
                             expense_categories=EXPENSE_CATEGORIES,
                             income_types=INCOME_TYPES)
    
    except Exception as e:
        flash(f'Error cargando dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', 
                             balance_summary={'balance': 0, 'total_income': 0, 'total_expense': 0},
                             monthly_summary={'total_income': 0, 'total_expense': 0, 'balance': 0},
                             recent_transactions=[],
                             category_analysis={'categories': {}})


@main_bp.route('/income')
def income_page():
    """Página para gestionar ingresos"""
    # Obtener ingresos recientes
    recent_income = transaction_service.get_transactions(
        transaction_type='income', 
        limit=20
    )
    
    # Resumen de ingresos por categoría (últimos 30 días)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    income_summary = db.session.query(
        Transaction.category,
        func.sum(Transaction.amount_cents).label('total_cents'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.transaction_type == 'income',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
        Transaction.is_active == True
    ).group_by(Transaction.category).all()
    
    # Convertir a formato amigable
    income_by_category = {}
    for category, total_cents, count in income_summary:
        income_by_category[category] = {
            'total': float(Decimal(total_cents) / 100),
            'count': count,
            'info': INCOME_TYPES.get(category, {'name': category, 'icon': '💰'})
        }
    
    return render_template('income.html',
                         recent_income=recent_income,
                         income_by_category=income_by_category,
                         income_types=INCOME_TYPES)


@main_bp.route('/expenses')
def expenses_page():
    """Página para gestionar gastos"""
    # Obtener gastos recientes
    recent_expenses = transaction_service.get_transactions(
        transaction_type='expense', 
        limit=20
    )
    
    # Análisis de gastos por categoría (último mes)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    category_analysis = transaction_service.get_category_analysis(start_date, end_date, 'USD')
    
    return render_template('expenses.html',
                         recent_expenses=recent_expenses,
                         category_analysis=category_analysis,
                         expense_categories=EXPENSE_CATEGORIES)


@main_bp.route('/reports')
def reports_page():
    """Página de reportes y análisis"""
    try:
        # Parámetros de fecha (por defecto último mes)
        end_date = date.today()
        start_date = request.args.get('start_date')
        end_date_param = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = end_date - timedelta(days=30)
        
        if end_date_param:
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        
        # Resumen del período
        transactions = transaction_service.get_transactions(start_date=start_date, end_date=end_date)
        
        # Calcular totales por moneda
        totals_by_currency = {}
        for transaction in transactions:
            currency = transaction.currency
            if currency not in totals_by_currency:
                totals_by_currency[currency] = {'income': 0, 'expense': 0}
            
            amount = float(transaction.amount_display)
            if transaction.transaction_type == 'income':
                totals_by_currency[currency]['income'] += amount
            else:
                totals_by_currency[currency]['expense'] += amount
        
        # Análisis de categorías
        category_analysis = transaction_service.get_category_analysis(start_date, end_date, 'USD')
        
        # Tendencias mensuales (últimos 6 meses)
        monthly_trends = []
        for i in range(6):
            trend_date = end_date - timedelta(days=30*i)
            monthly_summary = transaction_service.get_monthly_summary(
                trend_date.year, trend_date.month, 'USD'
            )
            monthly_summary['month_name'] = trend_date.strftime('%B %Y')
            monthly_trends.append(monthly_summary)
        
        monthly_trends.reverse()  # Orden cronológico
        
        # Top 10 transacciones por monto
        top_transactions = sorted(
            [t for t in transactions if t.transaction_type == 'expense'],
            key=lambda x: abs(x.amount),
            reverse=True
        )[:10]
        
        return render_template('reports.html',
                             start_date=start_date,
                             end_date=end_date,
                             totals_by_currency=totals_by_currency,
                             category_analysis=category_analysis,
                             monthly_trends=monthly_trends,
                             top_transactions=top_transactions,
                             transaction_count=len(transactions))
    
    except Exception as e:
        flash(f'Error generando reportes: {str(e)}', 'error')
        return render_template('reports.html',
                             start_date=start_date,
                             end_date=end_date,
                             totals_by_currency={},
                             category_analysis={'categories': {}},
                             monthly_trends=[],
                             top_transactions=[])


@main_bp.route('/settings')
def settings_page():
    """Página de configuración"""
    # Obtener cuentas activas
    accounts = Account.query.filter(Account.is_active == True).all()
    
    # Obtener tasas de cambio recientes
    recent_rates = ExchangeRate.query.filter(
        ExchangeRate.is_active == True
    ).order_by(ExchangeRate.created_at.desc()).limit(10).all()
    
    # Estadísticas de la base de datos
    stats = {
        'total_transactions': Transaction.query.filter(Transaction.is_active == True).count(),
        'total_accounts': Account.query.filter(Account.is_active == True).count(),
        'currencies_used': db.session.query(Transaction.currency).distinct().count(),
        'date_range': {
            'first': Transaction.query.order_by(Transaction.transaction_date.asc()).first(),
            'last': Transaction.query.order_by(Transaction.transaction_date.desc()).first()
        }
    }
    
    return render_template('settings.html',
                         accounts=accounts,
                         recent_rates=recent_rates,
                         stats=stats)


@main_bp.route('/exchange-rates')
def exchange_rates():
    """API endpoint para obtener tasas de cambio actuales"""
    try:
        # Obtener tasas principales
        rates = {}
        
        # USD a COP
        try:
            rates['USD_COP'] = float(exchange_service.get_exchange_rate('USD', 'COP'))
        except:
            rates['USD_COP'] = None
        
        # COP a USD
        try:
            rates['COP_USD'] = float(exchange_service.get_exchange_rate('COP', 'USD'))
        except:
            rates['COP_USD'] = None
        
        return jsonify({
            'success': True,
            'rates': rates,
            'updated_at': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main_bp.route('/convert')
def convert_currency():
    """API endpoint para convertir entre monedas"""
    try:
        amount = float(request.args.get('amount', 0))
        from_currency = request.args.get('from', 'USD').upper()
        to_currency = request.args.get('to', 'COP').upper()
        
        if amount <= 0:
            return jsonify({'error': 'Monto debe ser positivo'}), 400
        
        converted_amount = exchange_service.convert_amount(
            Decimal(str(amount)), from_currency, to_currency
        )
        
        rate = exchange_service.get_exchange_rate(from_currency, to_currency)
        
        return jsonify({
            'success': True,
            'original_amount': amount,
            'converted_amount': float(converted_amount),
            'from_currency': from_currency,
            'to_currency': to_currency,
            'exchange_rate': float(rate),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main_bp.route('/quick-stats')
def quick_stats():
    """API endpoint para estadísticas rápidas del dashboard"""
    try:
        today = date.today()
        
        # Balance actual
        balance = transaction_service.get_balance_summary('USD', today)
        
        # Transacciones de hoy
        today_transactions = transaction_service.get_transactions(
            start_date=today, end_date=today
        )
        
        today_income = sum(
            float(t.amount_usd or t.amount) for t in today_transactions 
            if t.transaction_type == 'income'
        )
        today_expense = sum(
            abs(float(t.amount_usd or t.amount)) for t in today_transactions 
            if t.transaction_type == 'expense'
        )
        
        return jsonify({
            'success': True,
            'balance_usd': balance['balance'],
            'today_income': today_income,
            'today_expense': today_expense,
            'transaction_count_today': len(today_transactions),
            'last_updated': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Funciones auxiliares
def calculate_percentage_change(old_value, new_value):
    """Calcula el cambio porcentual entre dos valores"""
    if old_value == 0:
        return 0 if new_value == 0 else 100
    
    change = ((new_value - old_value) / old_value) * 100
    return round(change, 1)


@main_bp.app_template_filter('money')
def money_filter(amount, currency='USD'):
    """Filtro para formatear moneda en templates"""
    if currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'COP':
        return f"${amount:,.0f} COP"
    else:
        return f"{amount:,.2f} {currency}"


@main_bp.app_template_filter('abs')
def abs_filter(value):
    """Filtro para valor absoluto"""
    return abs(value) if value is not None else 0


@main_bp.app_template_filter('percentage')
def percentage_filter(value, decimals=1):
    """Filtro para formatear porcentajes"""
    if value is None:
        return "0.0%"
    return f"{value:.{decimals}f}%"