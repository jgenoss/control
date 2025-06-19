"""
API REST para la aplicación financiera
Endpoints para estadísticas, reportes y gestión de datos
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, extract, and_, or_
import json

from models.models import db, Transaction, Account, ExchangeRate, Budget
from services.transaction_service import get_transaction_service, TransactionError
from services.exchange_service import get_exchange_service, ExchangeRateError
from config import EXPENSE_CATEGORIES, INCOME_TYPES

# Crear blueprint
api_bp = Blueprint('api', __name__)

# Servicios
transaction_service = get_transaction_service()
exchange_service = get_exchange_service()


# Decorador para manejo de errores
def api_error_handler(func):
    """Decorador para manejo consistente de errores en API"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (TransactionError, ExchangeRateError) as e:
            return jsonify({'error': str(e), 'type': 'business_error'}), 400
        except (ValueError, InvalidOperation) as e:
            return jsonify({'error': f'Datos inválidos: {str(e)}', 'type': 'validation_error'}), 400
        except Exception as e:
            current_app.logger.error(f'Error en API {func.__name__}: {str(e)}')
            return jsonify({'error': 'Error interno del servidor', 'type': 'server_error'}), 500
    wrapper.__name__ = func.__name__
    return wrapper


# === ENDPOINTS DE TRANSACCIONES ===

@api_bp.route('/transactions', methods=['GET'])
@api_error_handler
def get_transactions():
    """Obtiene lista de transacciones con filtros y paginación"""
    # Parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Parámetros de filtro
    transaction_type = request.args.get('type')
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    
    # Construir query base
    query = Transaction.query.filter(Transaction.is_active == True)
    
    # Aplicar filtros
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if category:
        query = query.filter(Transaction.category == category)
    
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Transaction.transaction_date >= start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Transaction.transaction_date <= end_date_obj)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                Transaction.description.ilike(search_pattern),
                Transaction.notes.ilike(search_pattern)
            )
        )
    
    # Ordenar por fecha descendente
    query = query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
    
    # Paginar
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    
    # Convertir a diccionarios
    transaction_list = [t.to_dict() for t in transactions]
    
    return jsonify({
        'success': True,
        'data': transaction_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@api_bp.route('/transactions', methods=['POST'])
@api_error_handler
def create_transaction():
    """Crea una nueva transacción"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No se enviaron datos'}), 400
    
    # Validar campos requeridos
    required_fields = ['amount', 'description', 'category', 'transaction_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo requerido: {field}'}), 400
    
    # Procesar fecha
    transaction_date = date.today()
    if 'transaction_date' in data:
        transaction_date = datetime.strptime(data['transaction_date'], '%Y-%m-%d').date()
    
    # Crear transacción según el tipo
    if data['transaction_type'] == 'income':
        transaction = transaction_service.create_income(
            amount=Decimal(str(data['amount'])),
            currency=data.get('currency', 'COP'),
            description=data['description'],
            category=data['category'],
            transaction_date=transaction_date,
            notes=data.get('notes'),
            tags=data.get('tags', [])
        )
    elif data['transaction_type'] == 'expense':
        transaction = transaction_service.create_expense(
            amount=Decimal(str(data['amount'])),
            currency=data.get('currency', 'USD'),
            description=data['description'],
            category=data['category'],
            subcategory=data.get('subcategory'),
            transaction_date=transaction_date,
            notes=data.get('notes'),
            tags=data.get('tags', [])
        )
    else:
        return jsonify({'error': 'Tipo de transacción inválido'}), 400
    
    return jsonify({
        'success': True,
        'data': transaction.to_dict(),
        'message': 'Transacción creada exitosamente'
    }), 201


@api_bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@api_error_handler
def get_transaction(transaction_id):
    """Obtiene una transacción específica"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if not transaction.is_active:
        return jsonify({'error': 'Transacción no encontrada'}), 404
    
    return jsonify({
        'success': True,
        'data': transaction.to_dict()
    })


@api_bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
@api_error_handler
def update_transaction(transaction_id):
    """Actualiza una transacción existente"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No se enviaron datos'}), 400
    
    # Filtrar campos actualizables
    updateable_fields = ['description', 'category', 'subcategory', 'notes', 'transaction_date', 'amount']
    update_data = {k: v for k, v in data.items() if k in updateable_fields}
    
    # Procesar fecha si está presente
    if 'transaction_date' in update_data:
        update_data['transaction_date'] = datetime.strptime(update_data['transaction_date'], '%Y-%m-%d').date()
    
    # Procesar monto si está presente
    if 'amount' in update_data:
        update_data['amount'] = Decimal(str(update_data['amount']))
    
    transaction = transaction_service.update_transaction(transaction_id, **update_data)
    
    return jsonify({
        'success': True,
        'data': transaction.to_dict(),
        'message': 'Transacción actualizada exitosamente'
    })


@api_bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@api_error_handler
def delete_transaction(transaction_id):
    """Elimina una transacción"""
    permanent = request.args.get('permanent', 'false').lower() == 'true'
    
    success = transaction_service.delete_transaction(transaction_id, soft_delete=not permanent)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Transacción eliminada exitosamente'
        })
    else:
        return jsonify({'error': 'Error eliminando transacción'}), 500


# === ENDPOINTS DE ESTADÍSTICAS ===

@api_bp.route('/stats/balance', methods=['GET'])
@api_error_handler
def get_balance_stats():
    """Obtiene estadísticas de balance"""
    currency = request.args.get('currency', 'USD')
    as_of_date = request.args.get('as_of_date')
    
    if as_of_date:
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
    else:
        as_of_date = date.today()
    
    balance_summary = transaction_service.get_balance_summary(currency, as_of_date)
    
    return jsonify({
        'success': True,
        'data': balance_summary
    })


@api_bp.route('/stats/monthly', methods=['GET'])
@api_error_handler
def get_monthly_stats():
    """Obtiene estadísticas mensuales"""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    currency = request.args.get('currency', 'USD')
    
    monthly_summary = transaction_service.get_monthly_summary(year, month, currency)
    
    return jsonify({
        'success': True,
        'data': monthly_summary
    })


@api_bp.route('/stats/categories', methods=['GET'])
@api_error_handler
def get_category_stats():
    """Obtiene estadísticas por categorías"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    currency = request.args.get('currency', 'USD')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    category_analysis = transaction_service.get_category_analysis(start_date, end_date, currency)
    
    return jsonify({
        'success': True,
        'data': category_analysis
    })


@api_bp.route('/stats/trends', methods=['GET'])
@api_error_handler
def get_trend_stats():
    """Obtiene tendencias de ingresos y gastos"""
    months = request.args.get('months', 6, type=int)
    currency = request.args.get('currency', 'USD')
    
    trends = []
    today = date.today()
    
    for i in range(months):
        # Calcular fecha del mes
        month_date = today - timedelta(days=30 * i)
        year = month_date.year
        month = month_date.month
        
        # Obtener resumen del mes
        summary = transaction_service.get_monthly_summary(year, month, currency)
        summary['month_year'] = f"{year}-{month:02d}"
        summary['month_name'] = month_date.strftime('%B %Y')
        
        trends.append(summary)
    
    # Ordenar cronológicamente
    trends.reverse()
    
    return jsonify({
        'success': True,
        'data': {
            'currency': currency,
            'months': months,
            'trends': trends
        }
    })


# === ENDPOINTS DE TASAS DE CAMBIO ===

@api_bp.route('/exchange-rates/current', methods=['GET'])
@api_error_handler
def get_current_rates():
    """Obtiene tasas de cambio actuales"""
    from_currency = request.args.get('from', 'USD')
    to_currency = request.args.get('to', 'COP')
    
    rate = exchange_service.get_exchange_rate(from_currency, to_currency)
    
    return jsonify({
        'success': True,
        'data': {
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': float(rate),
            'timestamp': datetime.now().isoformat()
        }
    })


@api_bp.route('/exchange-rates/convert', methods=['POST'])
@api_error_handler
def convert_currency():
    """Convierte un monto entre monedas"""
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'error': 'Monto requerido'}), 400
    
    amount = Decimal(str(data['amount']))
    from_currency = data.get('from_currency', 'USD')
    to_currency = data.get('to_currency', 'COP')
    
    converted_amount = exchange_service.convert_amount(amount, from_currency, to_currency)
    rate = exchange_service.get_exchange_rate(from_currency, to_currency)
    
    return jsonify({
        'success': True,
        'data': {
            'original_amount': float(amount),
            'converted_amount': float(converted_amount),
            'from_currency': from_currency,
            'to_currency': to_currency,
            'exchange_rate': float(rate),
            'timestamp': datetime.now().isoformat()
        }
    })


@api_bp.route('/exchange-rates/history', methods=['GET'])
@api_error_handler
def get_rate_history():
    """Obtiene historial de tasas de cambio"""
    from_currency = request.args.get('from', 'USD')
    to_currency = request.args.get('to', 'COP')
    days = request.args.get('days', 30, type=int)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    rates = ExchangeRate.query.filter(
        ExchangeRate.from_currency == from_currency,
        ExchangeRate.to_currency == to_currency,
        ExchangeRate.date >= start_date,
        ExchangeRate.date <= end_date,
        ExchangeRate.is_active == True
    ).order_by(ExchangeRate.date.desc()).all()
    
    rate_history = [rate.to_dict() for rate in rates]
    
    return jsonify({
        'success': True,
        'data': {
            'from_currency': from_currency,
            'to_currency': to_currency,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'rates': rate_history
        }
    })


@api_bp.route('/exchange-rates/update', methods=['POST'])
@api_error_handler
def update_exchange_rates():
    """Fuerza actualización de tasas de cambio"""
    results = exchange_service.update_all_rates()
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    return jsonify({
        'success': True,
        'data': {
            'updated_rates': success_count,
            'total_rates': total_count,
            'success_rate': (success_count / total_count * 100) if total_count > 0 else 0,
            'details': results
        },
        'message': f'Actualizadas {success_count} de {total_count} tasas'
    })


# === ENDPOINTS DE REPORTES ===

@api_bp.route('/reports/export', methods=['GET'])
@api_error_handler
def export_transactions():
    """Exporta transacciones en formato JSON"""
    # Parámetros de filtro
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    transaction_type = request.args.get('type')
    format_type = request.args.get('format', 'json')  # json, csv
    
    # Obtener transacciones
    filters = {}
    if start_date:
        filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d').date()
    if transaction_type:
        filters['transaction_type'] = transaction_type
    
    transactions = transaction_service.get_transactions(**filters)
    
    if format_type == 'csv':
        # Generar CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'fecha', 'tipo', 'categoria', 'subcategoria', 'descripcion',
            'monto', 'moneda', 'monto_usd', 'notas', 'creado'
        ])
        
        # Datos
        for t in transactions:
            writer.writerow([
                t.transaction_date.isoformat(),
                t.transaction_type,
                t.category,
                t.subcategory or '',
                t.description,
                float(t.amount_display),
                t.currency,
                float(t.amount_usd) if t.amount_usd else '',
                t.notes or '',
                t.created_at.isoformat()
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=transactions_{date.today().isoformat()}.csv'}
        )
    
    else:
        # Formato JSON
        export_data = {
            'export_date': datetime.now().isoformat(),
            'filters': filters,
            'total_transactions': len(transactions),
            'transactions': [t.to_dict() for t in transactions]
        }
        
        return jsonify({
            'success': True,
            'data': export_data
        })


@api_bp.route('/reports/summary', methods=['GET'])
@api_error_handler
def get_financial_summary():
    """Obtiene resumen financiero completo"""
    # Parámetros
    period = request.args.get('period', 'month')  # month, quarter, year
    currency = request.args.get('currency', 'USD')
    
    today = date.today()
    
    if period == 'month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif period == 'quarter':
        quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, (quarter - 1) * 3 + 1, 1)
        end_date = today
    elif period == 'year':
        start_date = date(today.year, 1, 1)
        end_date = today
    else:
        return jsonify({'error': 'Período inválido'}), 400
    
    # Obtener datos del período
    balance_summary = transaction_service.get_balance_summary(currency, end_date)
    category_analysis = transaction_service.get_category_analysis(start_date, end_date, currency)
    
    # Transacciones del período
    period_transactions = transaction_service.get_transactions(start_date=start_date, end_date=end_date)
    
    # Calcular estadísticas adicionales
    daily_average_expense = 0
    if period_transactions:
        total_expenses = sum(
            abs(float(t.amount_display)) for t in period_transactions 
            if t.transaction_type == 'expense'
        )
        days_in_period = (end_date - start_date).days + 1
        daily_average_expense = total_expenses / days_in_period if days_in_period > 0 else 0
    
    summary = {
        'period': {
            'type': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'currency': currency,
        'balance': balance_summary,
        'categories': category_analysis,
        'statistics': {
            'transaction_count': len(period_transactions),
            'daily_average_expense': daily_average_expense,
            'largest_expense': max(
                (abs(float(t.amount_display)) for t in period_transactions if t.transaction_type == 'expense'),
                default=0
            ),
            'largest_income': max(
                (float(t.amount_display) for t in period_transactions if t.transaction_type == 'income'),
                default=0
            )
        }
    }
    
    return jsonify({
        'success': True,
        'data': summary
    })


# === ENDPOINTS DE CONFIGURACIÓN ===

@api_bp.route('/config/categories', methods=['GET'])
def get_categories():
    """Obtiene todas las categorías disponibles"""
    return jsonify({
        'success': True,
        'data': {
            'income_types': INCOME_TYPES,
            'expense_categories': EXPENSE_CATEGORIES
        }
    })


@api_bp.route('/config/currencies', methods=['GET'])
def get_supported_currencies():
    """Obtiene monedas soportadas"""
    return jsonify({
        'success': True,
        'data': {
            'currencies': current_app.config.get('SUPPORTED_CURRENCIES', ['USD', 'COP', 'EUR']),
            'default_income_currency': current_app.config.get('DEFAULT_INCOME_CURRENCY', 'COP'),
            'default_expense_currency': current_app.config.get('DEFAULT_EXPENSE_CURRENCY', 'USD')
        }
    })


# === MANEJO DE ERRORES ===

@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Endpoint no encontrado'}), 404


@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    return jsonify({'error': 'Método no permitido'}), 405


@api_bp.errorhandler(500)
def api_internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Error interno del servidor'}), 500