"""
Paquete de rutas para la aplicación financiera
Contiene todos los blueprints de la aplicación
"""

from routes.main import main_bp
from routes.transactions import transactions_bp
from routes.api import api_bp

__all__ = ['main_bp', 'transactions_bp', 'api_bp']