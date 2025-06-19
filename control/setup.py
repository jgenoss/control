#!/usr/bin/env python3
"""
Script de configuración e instalación para Control de Gastos Personales
Automatiza la instalación y configuración inicial de la aplicación
"""

import os
import sys
import subprocess
import shutil
import secrets
from pathlib import Path

def print_header():
    """Imprime el encabezado del script"""
    print("=" * 70)
    print("📊 CONTROL DE GASTOS PERSONALES - SETUP")
    print("=" * 70)
    print("Sistema de gestión financiera COP-USD")
    print("Configuración automática de la aplicación")
    print("=" * 70)
    print()

def check_python_version():
    """Verifica que la versión de Python sea compatible"""
    print("🐍 Verificando versión de Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} - Compatible")
    print()

def create_virtual_environment():
    """Crea un entorno virtual para el proyecto"""
    print("📦 Configurando entorno virtual...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        response = input("❓ El entorno virtual ya existe. ¿Recrear? (y/n): ")
        if response.lower() == 'y':
            shutil.rmtree(venv_path)
        else:
            print("✅ Usando entorno virtual existente")
            return
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Entorno virtual creado exitosamente")
    except subprocess.CalledProcessError:
        print("❌ Error creando entorno virtual")
        sys.exit(1)
    
    print()

def install_dependencies():
    """Instala las dependencias del proyecto"""
    print("📚 Instalando dependencias...")
    
    # Determinar el comando de activación según el OS
    if os.name == 'nt':  # Windows
        pip_path = Path("venv/Scripts/pip")
    else:  # Unix/Linux/MacOS
        pip_path = Path("venv/bin/pip")
    
    try:
        # Actualizar pip
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
        
        # Instalar dependencias
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        
        print("✅ Dependencias instaladas exitosamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: No se encontró el archivo requirements.txt")
        sys.exit(1)
    
    print()

def create_env_file():
    """Crea el archivo .env con configuración básica"""
    print("⚙️  Configurando variables de entorno...")
    
    env_file = Path(".env")
    
    if env_file.exists():
        response = input("❓ El archivo .env ya existe. ¿Sobrescribir? (y/n): ")
        if response.lower() != 'y':
            print("✅ Manteniendo archivo .env existente")
            return
    
    # Generar clave secreta segura
    secret_key = secrets.token_urlsafe(32)
    
    env_content = f"""# Configuración automática generada por setup.py
FLASK_ENV=development
SECRET_KEY={secret_key}
DEV_DATABASE_URL=sqlite:///financial_app_dev.db
TEST_DATABASE_URL=sqlite:///financial_app_test.db
LOG_TO_STDOUT=false
PORT=5000
HOST=0.0.0.0
SUPPORTED_CURRENCIES=USD,COP,EUR
DEFAULT_INCOME_CURRENCY=COP
DEFAULT_EXPENSE_CURRENCY=USD
EXCHANGE_RATE_CACHE_TIMEOUT=3600
FALLBACK_TO_XE=true
SQLALCHEMY_ECHO=false
FLASK_DEBUG=true

# Configuración de APIs de tasas de cambio (opcional)
# FIXER_API_KEY=tu_api_key_de_fixer_io
# EXCHANGERATE_API_KEY=tu_api_key_de_exchangerate_api

# Para producción, cambiar FLASK_ENV=production y configurar base de datos
# DATABASE_URL=postgresql://usuario:password@localhost/financial_app
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ Archivo .env creado con configuración básica")
    print()

def initialize_database():
    """Inicializa la base de datos"""
    print("🗄️  Inicializando base de datos...")
    
    # Determinar el comando de Python según el OS
    if os.name == 'nt':  # Windows
        python_path = Path("venv/Scripts/python")
    else:  # Unix/Linux/MacOS
        python_path = Path("venv/bin/python")
    
    try:
        # Inicializar la base de datos
        subprocess.run([str(python_path), "-c", """
from app import create_app
from models import db, init_default_accounts
import os

os.environ['FLASK_ENV'] = 'development'
app = create_app()

with app.app_context():
    print('Creando tablas...')
    db.create_all()
    print('Inicializando cuentas por defecto...')
    init_default_accounts(db)
    print('Base de datos inicializada exitosamente')
"""], check=True)
        
        print("✅ Base de datos inicializada exitosamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error inicializando base de datos: {e}")
        print("   Puedes ejecutar manualmente: flask init-db")
    
    print()

def create_sample_data():
    """Pregunta si crear datos de ejemplo"""
    print("📊 Datos de ejemplo...")
    
    response = input("❓ ¿Crear datos de ejemplo para probar la aplicación? (y/n): ")
    
    if response.lower() == 'y':
        # Determinar el comando de Python según el OS
        if os.name == 'nt':  # Windows
            python_path = Path("venv/Scripts/python")
        else:  # Unix/Linux/MacOS
            python_path = Path("venv/bin/python")
        
        try:
            subprocess.run([str(python_path), "-c", """
from app import create_app
from services.transaction_service import get_transaction_service
from datetime import date, timedelta
from decimal import Decimal
import random
import os

os.environ['FLASK_ENV'] = 'development'
app = create_app()

with app.app_context():
    service = get_transaction_service()
    
    # Crear ingresos de ejemplo
    income_data = [
        (Decimal('2500000'), 'Salario Diciembre', 'salario'),
        (Decimal('800000'), 'Freelance desarrollo web', 'freelance'),
        (Decimal('300000'), 'Venta de productos', 'venta'),
    ]
    
    for amount, description, category in income_data:
        transaction_date = date.today() - timedelta(days=random.randint(1, 30))
        service.create_income(amount, 'COP', description, category, transaction_date)
    
    # Crear gastos de ejemplo
    expense_data = [
        (Decimal('25.50'), 'Almuerzo restaurante', 'alimentacion'),
        (Decimal('45.00'), 'Supermercado semanal', 'alimentacion'),
        (Decimal('12.00'), 'Transporte público', 'transporte'),
        (Decimal('80.00'), 'Servicios de internet', 'servicios'),
        (Decimal('15.00'), 'Suscripción Netflix', 'entretenimiento'),
        (Decimal('35.00'), 'Medicamentos', 'salud'),
        (Decimal('60.00'), 'Compra ropa', 'ropa'),
    ]
    
    for amount, description, category in expense_data:
        transaction_date = date.today() - timedelta(days=random.randint(1, 30))
        service.create_expense(amount, 'USD', description, category, transaction_date)
    
    print('Datos de ejemplo creados exitosamente')
"""], check=True)
            
            print("✅ Datos de ejemplo creados exitosamente")
        except subprocess.CalledProcessError:
            print("❌ Error creando datos de ejemplo")
    else:
        print("⏭️  Datos de ejemplo omitidos")
    
    print()

def create_directories():
    """Crea directorios necesarios"""
    print("📁 Creando directorios necesarios...")
    
    directories = [
        "logs",
        "backups", 
        "static/css",
        "static/js", 
        "static/images",
        "templates/transactions",
        "templates/errors"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directorios creados")
    print()

def show_final_instructions():
    """Muestra las instrucciones finales"""
    print("🎉 ¡INSTALACIÓN COMPLETADA!")
    print("=" * 70)
    print()
    print("📋 Para ejecutar la aplicación:")
    print()
    
    if os.name == 'nt':  # Windows
        print("   1. Activar entorno virtual:")
        print("      venv\\Scripts\\activate")
        print()
        print("   2. Ejecutar la aplicación:")
        print("      python app.py")
    else:  # Unix/Linux/MacOS
        print("   1. Activar entorno virtual:")
        print("      source venv/bin/activate")
        print()
        print("   2. Ejecutar la aplicación:")
        print("      python app.py")
    
    print()
    print("🌐 La aplicación estará disponible en:")
    print("   http://localhost:5000")
    print()
    print("⚙️  Configuración adicional:")
    print("   • Edita el archivo .env para configurar APIs de tasas de cambio")
    print("   • Para producción, configura una base de datos PostgreSQL/MySQL")
    print("   • Revisa la documentación en README.md")
    print()
    print("🔑 APIs recomendadas para tasas de cambio:")
    print("   • Fixer.io (1000 requests/mes gratis)")
    print("   • ExchangeRate-API (1500 requests/mes gratis)")
    print()
    print("📧 Comandos útiles:")
    print("   flask init-db          # Reinicializar base de datos")
    print("   flask create-sample-data # Crear datos de ejemplo")
    print("   flask update-rates     # Actualizar tasas de cambio")
    print("   flask export-data      # Exportar datos a CSV")
    print()

def main():
    """Función principal del script de setup"""
    print_header()
    
    try:
        check_python_version()
        create_directories()
        create_virtual_environment()
        #install_dependencies()
        create_env_file()
        initialize_database()
        create_sample_data()
        show_final_instructions()
        
    except KeyboardInterrupt:
        print("\n❌ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()