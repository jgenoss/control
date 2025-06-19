# Configuración de entorno para Control de Gastos Personales
# Copia este archivo como .env y configura los valores

# ====================================
# CONFIGURACIÓN DE FLASK
# ====================================
FLASK_ENV=development
# Opciones: development, production, testing

# Clave secreta para Flask (CAMBIAR EN PRODUCCIÓN)
SECRET_KEY=tu-clave-secreta-muy-segura-aqui-cambiar-en-produccion

# ====================================
# BASE DE DATOS
# ====================================
# Para desarrollo (SQLite)
DEV_DATABASE_URL=sqlite:///financial_app_dev.db

# Para testing (SQLite)
TEST_DATABASE_URL=sqlite:///financial_app_test.db

# Para producción (PostgreSQL o MySQL)
# DATABASE_URL=postgresql://usuario:password@localhost/financial_app
# DATABASE_URL=mysql://usuario:password@localhost/financial_app

# ====================================
# REDIS (CACHE)
# ====================================
# URL de Redis para cache (opcional en desarrollo)
# REDIS_URL=redis://localhost:6379/0

# ====================================
# TASAS DE CAMBIO - APIs
# ====================================
# API Key de Fixer.io (registro gratuito en https://fixer.io/)
# FIXER_API_KEY=tu_api_key_de_fixer_io

# API Key de ExchangeRate-API (registro gratuito en https://exchangerate-api.com/)
# EXCHANGERATE_API_KEY=tu_api_key_de_exchangerate_api

# ====================================
# CONFIGURACIÓN DE LOGGING
# ====================================
# Enviar logs a stdout (útil para contenedores)
LOG_TO_STDOUT=false

# ====================================
# CONFIGURACIÓN DE SERVIDOR
# ====================================
# Puerto para el servidor
PORT=5000

# Host para el servidor
HOST=0.0.0.0

# ====================================
# CONFIGURACIÓN DE SEGURIDAD
# ====================================
# Configuración para HTTPS en producción
# SSL_CERT_PATH=/path/to/cert.pem
# SSL_KEY_PATH=/path/to/key.pem

# ====================================
# CONFIGURACIÓN DE EMAIL (OPCIONAL)
# ====================================
# Para notificaciones por email
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=tu_email@gmail.com
# MAIL_PASSWORD=tu_password_de_aplicacion

# ====================================
# CONFIGURACIÓN DE MONEDAS
# ====================================
# Monedas soportadas (separadas por coma)
SUPPORTED_CURRENCIES=USD,COP,EUR

# Moneda por defecto para ingresos
DEFAULT_INCOME_CURRENCY=COP

# Moneda por defecto para gastos
DEFAULT_EXPENSE_CURRENCY=USD

# ====================================
# CONFIGURACIÓN DE TASAS DE CAMBIO
# ====================================
# Tiempo de cache para tasas de cambio (en segundos)
EXCHANGE_RATE_CACHE_TIMEOUT=3600

# Habilitar web scraping de XE.com como fallback
FALLBACK_TO_XE=true

# ====================================
# CONFIGURACIÓN DE DESARROLLO
# ====================================
# Mostrar SQL queries en desarrollo
SQLALCHEMY_ECHO=false

# Modo debug de Flask
FLASK_DEBUG=true

# ====================================
# CONFIGURACIÓN DE RESPALDOS
# ====================================
# Directorio para respaldos automáticos
# BACKUP_DIR=/path/to/backups

# Frecuencia de respaldos en días
# BACKUP_FREQUENCY=7

# ====================================
# CONFIGURACIÓN DE CONTENEDORES
# ====================================
# Si usas Docker Compose
# POSTGRES_DB=financial_app
# POSTGRES_USER=financial_user
# POSTGRES_PASSWORD=secure_password
# REDIS_PASSWORD=redis_password

# ====================================
# CONFIGURACIÓN DE MONITOREO
# ====================================
# API key para servicios de monitoreo (Sentry, etc.)
# SENTRY_DSN=https://your-sentry-dsn

# ====================================
# NOTAS IMPORTANTES
# ====================================
# 1. NUNCA subas el archivo .env al control de versiones
# 2. En producción, cambia todas las claves y passwords
# 3. Usa variables de entorno del sistema en lugar de archivo .env en producción
# 4. Para API keys gratuitas de tasas de cambio:
#    - Fixer.io: 1000 requests/mes gratis
#    - ExchangeRate-API: 1500 requests/mes gratis
# 5. El web scraping de XE.com es solo fallback de emergencia