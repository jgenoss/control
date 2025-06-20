from datetime import datetime, date
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from sqlalchemy import func, desc, extract
from app import db
from models import User, Transaction, SystemSettings

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)

# ============ MAIN ROUTES ============

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Transaction.created_at)).limit(10).all()
    
    # Get monthly summary
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    monthly_income = db.session.query(func.sum(Transaction.amount_cop))\
        .filter_by(user_id=current_user.id, type='income')\
        .filter(extract('month', Transaction.date) == current_month)\
        .filter(extract('year', Transaction.date) == current_year).scalar() or 0
    
    monthly_expenses = db.session.query(func.sum(Transaction.amount_cop))\
        .filter_by(user_id=current_user.id, type='expense')\
        .filter(extract('month', Transaction.date) == current_month)\
        .filter(extract('year', Transaction.date) == current_year).scalar() or 0
    
    return render_template('dashboard.html', 
                         user=current_user,
                         recent_transactions=recent_transactions,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses,
                         monthly_balance=monthly_income - monthly_expenses)

@main_bp.route('/api/transactions', methods=['GET', 'POST'])
@login_required
def api_transactions():
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            transaction = Transaction()
            transaction.user_id = current_user.id
            transaction.type = data['type']
            transaction.amount = float(data['amount'])
            transaction.currency = data['currency']
            transaction.exchange_rate = float(data['exchange_rate'])
            transaction.category = data['category']
            transaction.description = data.get('description', '')
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            
            # Calculate COP equivalent
            if data['currency'] == 'USD':
                transaction.amount_cop = transaction.amount * transaction.exchange_rate
            else:
                transaction.amount_cop = transaction.amount
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Transacción guardada exitosamente'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error al guardar: {str(e)}'})
    
    else:
        # GET - Return user's transactions
        transactions = Transaction.query.filter_by(user_id=current_user.id)\
            .order_by(desc(Transaction.date)).all()
        
        return jsonify([{
            'id': t.id,
            'type': t.type,
            'amount': t.amount,
            'currency': t.currency,
            'amount_cop': t.amount_cop,
            'exchange_rate': t.exchange_rate,
            'category': t.category,
            'description': t.description,
            'date': t.date.strftime('%Y-%m-%d'),
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for t in transactions])

@main_bp.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()
    if not transaction:
        return jsonify({'success': False, 'message': 'Transacción no encontrada'})
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Transacción eliminada'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar: {str(e)}'})

# ============ AUTH ROUTES ============

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Por favor ingresa usuario y contraseña', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.active:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validation
        if not all([username, email, password, password_confirm, first_name, last_name]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')
        
        if password and len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return render_template('register.html')
        
        # Create user
        try:
            user = User()
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Cuenta creada exitosamente. Puedes iniciar sesión ahora.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la cuenta: {str(e)}', 'error')
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente', 'info')
    return redirect(url_for('auth.login'))

# ============ ADMIN ROUTES ============

def admin_required(f):
    """Decorator to require admin privileges"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    # Get statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(active=True).count()
    total_transactions = Transaction.query.count()
    
    # Recent users
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_transactions=total_transactions,
                         recent_users=recent_users)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta', 'error')
        return redirect(url_for('admin.users'))
    
    user.active = not user.active
    db.session.commit()
    
    status = 'activado' if user.active else 'desactivado'
    flash(f'Usuario {user.username} {status} exitosamente', 'success')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/admin')
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('No puedes modificar tus propios privilegios', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'otorgados' if user.is_admin else 'removidos'
    flash(f'Privilegios de administrador {status} para {user.username}', 'success')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        # Delete user and all their transactions (cascade)
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {user.username} eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')