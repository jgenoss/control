"""
Blueprint para gestión de transacciones
Maneja CRUD de ingresos y gastos
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

from models.models import db, Transaction
from services.transaction_service import get_transaction_service, TransactionError
from config import EXPENSE_CATEGORIES, INCOME_TYPES

# Crear blueprint
transactions_bp = Blueprint('transactions', __name__)
transaction_service = get_transaction_service()


# Formularios WTF
class IncomeForm(FlaskForm):
    """Formulario para crear/editar ingresos"""
    amount = DecimalField('Monto (COP)', validators=[
        DataRequired(message='El monto es requerido'),
        NumberRange(min=0.01, message='El monto debe ser positivo')
    ], places=2)
    
    description = StringField('Descripción', validators=[
        DataRequired(message='La descripción es requerida'),
        Length(max=255, message='Descripción muy larga')
    ])
    
    category = SelectField('Categoría', validators=[DataRequired()], 
                          choices=[(k, v['name']) for k, v in INCOME_TYPES.items()])
    
    transaction_date = DateField('Fecha', validators=[DataRequired()], 
                                default=date.today)
    
    notes = TextAreaField('Notas', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Guardar Ingreso')


class ExpenseForm(FlaskForm):
    """Formulario para crear/editar gastos"""
    amount = DecimalField('Monto (USD)', validators=[
        DataRequired(message='El monto es requerido'),
        NumberRange(min=0.01, message='El monto debe ser positivo')
    ], places=2)
    
    description = StringField('Descripción', validators=[
        DataRequired(message='La descripción es requerida'),
        Length(max=255, message='Descripción muy larga')
    ])
    
    category = SelectField('Categoría', validators=[DataRequired()], 
                          choices=[(k, v['name']) for k, v in EXPENSE_CATEGORIES.items()])
    
    subcategory = StringField('Subcategoría', validators=[
        Optional(), Length(max=50)
    ])
    
    transaction_date = DateField('Fecha', validators=[DataRequired()], 
                                default=date.today)
    
    notes = TextAreaField('Notas', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Guardar Gasto')


@transactions_bp.route('/')
def list_transactions():
    """Lista todas las transacciones con filtros"""
    # Parámetros de filtro
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    transaction_type = request.args.get('type', '')
    category = request.args.get('category', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Construir filtros
    filters = {}
    if transaction_type:
        filters['transaction_type'] = transaction_type
    if category:
        filters['category'] = category
    if start_date:
        try:
            filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Fecha de inicio inválida', 'error')
    if end_date:
        try:
            filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Fecha de fin inválida', 'error')
    
    # Obtener transacciones
    offset = (page - 1) * per_page
    transactions = transaction_service.get_transactions(
        limit=per_page, 
        offset=offset,
        **filters
    )
    
    # Calcular totales para la página actual
    total_income = sum(
        float(t.amount_display) for t in transactions 
        if t.transaction_type == 'income'
    )
    total_expense = sum(
        float(t.amount_display) for t in transactions 
        if t.transaction_type == 'expense'
    )
    
    # Información de paginación
    total_count = len(transaction_service.get_transactions(**filters))
    has_next = total_count > (page * per_page)
    has_prev = page > 1
    
    return render_template('transactions/list.html',
                         transactions=transactions,
                         total_income=total_income,
                         total_expense=total_expense,
                         expense_categories=EXPENSE_CATEGORIES,
                         income_types=INCOME_TYPES,
                         current_filters={
                             'type': transaction_type,
                             'category': category,
                             'start_date': start_date,
                             'end_date': end_date
                         },
                         pagination={
                             'page': page,
                             'has_next': has_next,
                             'has_prev': has_prev,
                             'next_page': page + 1 if has_next else None,
                             'prev_page': page - 1 if has_prev else None
                         })


@transactions_bp.route('/income/new', methods=['GET', 'POST'])
def create_income():
    """Crear nuevo ingreso"""
    form = IncomeForm()
    
    if form.validate_on_submit():
        try:
            transaction = transaction_service.create_income(
                amount=form.amount.data,
                currency='COP',  # Los ingresos son en COP según requerimientos
                description=form.description.data,
                category=form.category.data,
                transaction_date=form.transaction_date.data,
                notes=form.notes.data
            )
            
            flash(f'Ingreso creado: {form.amount.data:,.0f} COP - {form.description.data}', 'success')
            return redirect(url_for('transactions.list_transactions'))
            
        except TransactionError as e:
            flash(f'Error creando ingreso: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error inesperado: {str(e)}', 'error')
    
    return render_template('transactions/create_income.html', form=form)


@transactions_bp.route('/expense/new', methods=['GET', 'POST'])
def create_expense():
    """Crear nuevo gasto"""
    form = ExpenseForm()
    
    if form.validate_on_submit():
        try:
            transaction = transaction_service.create_expense(
                amount=form.amount.data,
                currency='USD',  # Los gastos son en USD según requerimientos
                description=form.description.data,
                category=form.category.data,
                subcategory=form.subcategory.data,
                transaction_date=form.transaction_date.data,
                notes=form.notes.data
            )
            
            flash(f'Gasto creado: ${form.amount.data:.2f} USD - {form.description.data}', 'success')
            return redirect(url_for('transactions.list_transactions'))
            
        except TransactionError as e:
            flash(f'Error creando gasto: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error inesperado: {str(e)}', 'error')
    
    return render_template('transactions/create_expense.html', form=form)


@transactions_bp.route('/<int:transaction_id>')
def view_transaction(transaction_id):
    """Ver detalles de una transacción"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Información adicional
    conversion_info = None
    if transaction.exchange_rate:
        conversion_info = {
            'rate': float(transaction.exchange_rate.rate),
            'source': transaction.exchange_rate.source,
            'date': transaction.exchange_rate.date.isoformat()
        }
    
    return render_template('transactions/detail.html',
                         transaction=transaction,
                         conversion_info=conversion_info,
                         category_info=get_category_info(transaction.category, transaction.transaction_type))


@transactions_bp.route('/<int:transaction_id>/edit', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    """Editar una transacción existente"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Crear formulario apropiado según el tipo
    if transaction.transaction_type == 'income':
        form = IncomeForm(obj=transaction)
        template = 'transactions/edit_income.html'
        # Ajustar el monto para mostrar el valor positivo
        form.amount.data = abs(transaction.amount)
    else:
        form = ExpenseForm(obj=transaction)
        template = 'transactions/edit_expense.html'
        # Ajustar el monto para mostrar el valor positivo
        form.amount.data = abs(transaction.amount)
    
    if form.validate_on_submit():
        try:
            # Preparar datos de actualización
            update_data = {
                'description': form.description.data,
                'category': form.category.data,
                'transaction_date': form.transaction_date.data,
                'notes': form.notes.data
            }
            
            # Ajustar monto según el tipo de transacción
            if transaction.transaction_type == 'income':
                update_data['amount'] = form.amount.data
            else:
                update_data['amount'] = -form.amount.data  # Negativo para gastos
                if hasattr(form, 'subcategory'):
                    update_data['subcategory'] = form.subcategory.data
            
            # Actualizar la transacción
            updated_transaction = transaction_service.update_transaction(
                transaction_id, **update_data
            )
            
            flash(f'Transacción actualizada exitosamente', 'success')
            return redirect(url_for('transactions.view_transaction', transaction_id=transaction_id))
            
        except TransactionError as e:
            flash(f'Error actualizando transacción: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error inesperado: {str(e)}', 'error')
    
    return render_template(template, form=form, transaction=transaction)


@transactions_bp.route('/<int:transaction_id>/delete', methods=['POST'])
def delete_transaction(transaction_id):
    """Eliminar una transacción"""
    try:
        success = transaction_service.delete_transaction(transaction_id, soft_delete=True)
        if success:
            flash('Transacción eliminada exitosamente', 'success')
        else:
            flash('Error eliminando transacción', 'error')
    except TransactionError as e:
        flash(f'Error: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'error')
    
    return redirect(url_for('transactions.list_transactions'))


# API Endpoints JSON
@transactions_bp.route('/api/quick-add-income', methods=['POST'])
def api_quick_add_income():
    """API para agregar ingreso rápidamente"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data or 'amount' not in data or 'description' not in data:
            return jsonify({'error': 'Faltan datos requeridos'}), 400
        
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            return jsonify({'error': 'El monto debe ser positivo'}), 400
        
        transaction = transaction_service.create_income(
            amount=amount,
            currency='COP',
            description=data['description'],
            category=data.get('category', 'otros'),
            transaction_date=date.today() if not data.get('date') else 
                           datetime.strptime(data['date'], '%Y-%m-%d').date(),
            notes=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(),
            'message': f'Ingreso de {amount:,.0f} COP agregado'
        })
        
    except (ValueError, InvalidOperation):
        return jsonify({'error': 'Monto inválido'}), 400
    except TransactionError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500


@transactions_bp.route('/api/quick-add-expense', methods=['POST'])
def api_quick_add_expense():
    """API para agregar gasto rápidamente"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data or 'amount' not in data or 'description' not in data or 'category' not in data:
            return jsonify({'error': 'Faltan datos requeridos'}), 400
        
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            return jsonify({'error': 'El monto debe ser positivo'}), 400
        
        if data['category'] not in EXPENSE_CATEGORIES:
            return jsonify({'error': 'Categoría inválida'}), 400
        
        transaction = transaction_service.create_expense(
            amount=amount,
            currency='USD',
            description=data['description'],
            category=data['category'],
            subcategory=data.get('subcategory'),
            transaction_date=date.today() if not data.get('date') else 
                           datetime.strptime(data['date'], '%Y-%m-%d').date(),
            notes=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(),
            'message': f'Gasto de ${amount:.2f} USD agregado'
        })
        
    except (ValueError, InvalidOperation):
        return jsonify({'error': 'Monto inválido'}), 400
    except TransactionError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500


@transactions_bp.route('/api/categories/<transaction_type>')
def api_get_categories(transaction_type):
    """API para obtener categorías según el tipo de transacción"""
    if transaction_type == 'income':
        categories = INCOME_TYPES
    elif transaction_type == 'expense':
        categories = EXPENSE_CATEGORIES
    else:
        return jsonify({'error': 'Tipo de transacción inválido'}), 400
    
    return jsonify({
        'success': True,
        'categories': categories
    })


@transactions_bp.route('/api/summary')
def api_transaction_summary():
    """API para obtener resumen de transacciones"""
    try:
        # Parámetros opcionales
        days = request.args.get('days', 30, type=int)
        currency = request.args.get('currency', 'USD')
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Obtener resumen del período
        transactions = transaction_service.get_transactions(start_date=start_date, end_date=end_date)
        
        summary = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'currency': currency,
            'totals': {
                'income': 0,
                'expense': 0,
                'balance': 0,
                'transaction_count': len(transactions)
            },
            'by_category': {}
        }
        
        # Calcular totales
        for transaction in transactions:
            # Convertir a moneda solicitada si es necesario
            if transaction.currency == currency:
                amount = float(transaction.amount_display)
            elif currency == 'USD' and transaction.amount_usd:
                amount = float(transaction.amount_usd)
            else:
                # TODO: Implementar conversión usando exchange service
                amount = float(transaction.amount_display)
            
            if transaction.transaction_type == 'income':
                summary['totals']['income'] += amount
            else:
                summary['totals']['expense'] += amount
                
                # Agrupar gastos por categoría
                category = transaction.category
                if category not in summary['by_category']:
                    summary['by_category'][category] = {
                        'amount': 0,
                        'count': 0,
                        'info': EXPENSE_CATEGORIES.get(category, {'name': category})
                    }
                
                summary['by_category'][category]['amount'] += amount
                summary['by_category'][category]['count'] += 1
        
        summary['totals']['balance'] = summary['totals']['income'] - summary['totals']['expense']
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Funciones auxiliares
def get_category_info(category, transaction_type):
    """Obtiene información de la categoría según el tipo de transacción"""
    if transaction_type == 'income':
        return INCOME_TYPES.get(category, {'name': category, 'icon': '💰'})
    else:
        return EXPENSE_CATEGORIES.get(category, {'name': category, 'icon': '📦'})


@transactions_bp.app_template_filter('transaction_icon')
def transaction_icon_filter(transaction):
    """Filtro para obtener el icono de una transacción"""
    category_info = get_category_info(transaction.category, transaction.transaction_type)
    return category_info.get('icon', '💰' if transaction.transaction_type == 'income' else '💸')


@transactions_bp.app_template_filter('transaction_color')
def transaction_color_filter(transaction):
    """Filtro para obtener el color de una transacción"""
    if transaction.transaction_type == 'income':
        return 'success'
    else:
        return 'danger'