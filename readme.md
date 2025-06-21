# 💰 Control de Gastos Personales COP/USD

Una aplicación web progresiva (PWA) desarrollada en Flask para gestionar finanzas personales entre Pesos Colombianos y Dólares Americanos con conversión automática de moneda y análisis de impacto del tipo de cambio.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#licencia)
[![PWA](https://img.shields.io/badge/PWA-Ready-purple.svg)]()

## 🌟 Características Principales

- **💱 Soporte Multi-Moneda**: Manejo de transacciones en Pesos Colombianos (COP) y Dólares Americanos (USD)
- **🔄 Conversión Automática**: Obtención de tipos de cambio en tiempo real desde APIs confiables
- **📊 Visualización de Datos**: Gráficos interactivos para análisis de gastos por categoría y tendencias mensuales
- **📈 Análisis de Impacto**: Evaluación del impacto de las variaciones del tipo de cambio en tu patrimonio
- **📱 Aplicación Web Progresiva**: Instalable en dispositivos móviles y de escritorio
- **🎨 Diseño Responsivo**: Interfaz optimizada para todos los tamaños de pantalla
- **💾 Almacenamiento Dual**: Datos almacenados localmente y con soporte para base de datos
- **🔒 Datos Seguros**: Manejo seguro de información financiera personal

## 🚀 Demo en Vivo

[Ver Demo](https://tu-dominio.com) | [Instalar PWA](https://tu-dominio.com/#install)

## 📸 Capturas de Pantalla

| Dashboard Principal | Registro de Transacciones | Reportes y Análisis |
|---------------------|---------------------------|---------------------|
| ![Dashboard](screenshots/dashboard.png) | ![Transactions](screenshots/transactions.png) | ![Reports](screenshots/reports.png) |

## 🛠️ Tecnologías Utilizadas

### Backend
- **Flask 2.3+** - Framework web de Python
- **SQLAlchemy** - ORM para manejo de base de datos
- **Flask-SQLAlchemy** - Integración de SQLAlchemy con Flask

### Frontend
- **JavaScript ES6+** - Lógica del cliente
- **Chart.js 3.9+** - Visualización de datos
- **Bootstrap 5.3** - Framework CSS
- **Bootstrap Icons** - Iconografía

### APIs y Servicios
- **Exchange Rates API** - Tipos de cambio en tiempo real
- **PWA Manifest** - Funcionalidades de aplicación progresiva

### Base de Datos
- **SQLite** (desarrollo)
- **PostgreSQL** (producción - opcional)

## 📋 Prerrequisitos

- **Python 3.8+**
- **pip** (gestor de paquetes de Python)
- **Git** (para clonar el repositorio)
- Conexión a internet (para obtener tipos de cambio)

## ⚡ Instalación Rápida

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/control-gastos-cop-usd.git
cd control-gastos-cop-usd

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python main.py
```

La aplicación estará disponible en `http://localhost:5000`

## 🔧 Instalación Detallada

### 1. Preparación del Entorno

```bash
# Verificar versión de Python
python --version  # Debe ser 3.8 o superior

# Clonar el repositorio
git clone https://github.com/tu-usuario/control-gastos-cop-usd.git
cd control-gastos-cop-usd
```

### 2. Configuración del Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Linux/MacOS:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

### 3. Instalación de Dependencias

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias del proyecto
pip install -r requirements.txt
```

### 4. Configuración de Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Configuración de la aplicación
SECRET_KEY=tu_clave_secreta_muy_segura_aqui
FLASK_ENV=development

# Base de datos (opcional)
DATABASE_URL=sqlite:///expenses.db

# API de tipos de cambio (opcional - usa valor por defecto si no se especifica)
EXCHANGE_API_KEY=tu_api_key_aqui
```

### 5. Inicialización de la Base de Datos

```bash
# La base de datos se crea automáticamente al ejecutar la aplicación
python main.py
```

### 6. Verificación de la Instalación

1. Abre tu navegador en `http://localhost:5000`
2. Verifica que la página principal carga correctamente
3. Prueba registrar una transacción de prueba
4. Confirma que los tipos de cambio se obtienen correctamente

## 📖 Guía de Uso

### Registro de Ingresos

1. Navega a la pestaña **"Ingresos"**
2. Ingresa el monto en COP o USD
3. Añade una descripción descriptiva
4. Selecciona la fecha de la transacción
5. Haz clic en **"Registrar Ingreso"**

### Registro de Gastos

1. Ve a la pestaña **"Gastos"**
2. Ingresa el monto y selecciona la moneda
3. Elige una categoría (Alimentación, Transporte, etc.)
4. Añade una descripción
5. Confirma la fecha y registra el gasto

### Análisis de Datos

- **Dashboard**: Vista general de balance, ingresos y gastos del mes
- **Historial**: Lista completa de transacciones con filtros
- **Reportes**: Gráficos de tendencias y comparaciones mensuales
- **Impacto TRM**: Análisis del efecto de las variaciones del tipo de cambio

### Funcionalidades PWA

- **Instalación**: Usa el botón "Instalar App" cuando aparezca
- **Uso Offline**: Funcionalidad básica disponible sin conexión
- **Notificaciones**: Recordatorios para registrar gastos (próximamente)

## 🔧 Configuración Avanzada

### Variables de Entorno Completas

```env
# Configuración principal
SECRET_KEY=clave_secreta_produccion_muy_larga_y_segura
FLASK_ENV=production

# Base de datos
DATABASE_URL=postgresql://usuario:contraseña@localhost/gastos_db

# APIs externas
EXCHANGE_API_KEY=tu_clave_api_tipos_cambio
EXCHANGE_API_URL=https://api.exchangerate-api.com/v4/latest/USD

# Configuración de sesión
SESSION_TIMEOUT=3600
```

### Configuración para Producción

```bash
# Usar servidor WSGI para producción
pip install gunicorn

# Ejecutar con Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### Configuración de Base de Datos PostgreSQL

```bash
# Instalar dependencias adicionales
pip install psycopg2-binary

# Configurar variable de entorno
export DATABASE_URL="postgresql://usuario:contraseña@localhost/gastos_db"
```

## 🐳 Docker (Opcional)

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "main.py"]
```

```bash
# Construir y ejecutar
docker build -t gastos-app .
docker run -p 5000:5000 gastos-app
```

## 🧪 Desarrollo y Testing

### Estructura del Proyecto

```
control-gastos-cop-usd/
├── app.py                 # Configuración principal de Flask
├── main.py               # Punto de entrada de la aplicación
├── requirements.txt      # Dependencias de Python
├── static/              # Archivos estáticos
│   ├── styles.css       # Estilos CSS personalizados
│   ├── script.js        # Lógica JavaScript principal
│   ├── manifest.json    # Configuración PWA
│   └── sw.js           # Service Worker
├── templates/           # Plantillas HTML
│   └── index.html      # Plantilla principal
└── README.md           # Este archivo
```

### Modo de Desarrollo

```bash
# Activar modo debug
export FLASK_ENV=development
export FLASK_DEBUG=1

# Ejecutar con recarga automática
python main.py
```

### Personalización

- **Estilos**: Modifica `static/styles.css` para cambiar la apariencia
- **Funcionalidad**: Extiende `static/script.js` para nuevas características
- **Categorías**: Añade categorías de gastos en el archivo HTML
- **Monedas**: Configura soporte para monedas adicionales

## 🔐 Seguridad y Privacidad

### Medidas de Seguridad Implementadas

- **Claves Secretas**: Configuración segura de sesiones Flask
- **Validación de Datos**: Sanitización de entradas de usuario
- **HTTPS Ready**: Configuración preparada para SSL/TLS
- **Almacenamiento Local**: Datos almacenados localmente en el navegador

### Consideraciones de Privacidad

⚠️ **Importante**: Esta aplicación está diseñada para uso personal. Los datos se almacenan localmente en tu navegador y/o en tu base de datos personal. No se envían datos financieros a servidores externos excepto para obtener tipos de cambio.

### Recomendaciones de Seguridad

1. **Usa HTTPS** en producción
2. **Cambia las claves secretas** por defecto
3. **Realiza copias de seguridad** de tu base de datos regularmente
4. **Mantén actualizado** el software y dependencias

## 🤝 Contribuir al Proyecto

¡Las contribuciones son bienvenidas! Aquí te explico cómo puedes ayudar:

### Reportar Problemas

1. Verifica que el problema no haya sido reportado previamente
2. Usa el [template de issues](https://github.com/tu-usuario/control-gastos-cop-usd/issues/new)
3. Incluye información detallada del problema y pasos para reproducirlo

### Enviar Mejoras

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Áreas de Contribución

- 🐛 **Corrección de bugs**
- ✨ **Nuevas características**
- 📝 **Mejora de documentación**
- 🌐 **Internacionalización**
- 🧪 **Testing**
- 🎨 **Mejoras de UI/UX**

## 🗺️ Roadmap

### Versión 1.1 (Próximo Release)
- [ ] Soporte para más monedas (EUR, GBP)
- [ ] Exportación de datos a CSV/Excel
- [ ] Notificaciones push
- [ ] Modo oscuro

### Versión 1.2 (Futuro)
- [ ] Sincronización en la nube (opcional)
- [ ] Metas de ahorro
- [ ] Predicciones basadas en IA
- [ ] API REST completa

### Ideas para el Futuro
- [ ] Aplicación móvil nativa
- [ ] Integración con bancos (API Bancolombia, etc.)
- [ ] Alertas de gastos por categoría
- [ ] Reportes personalizables

## ❓ FAQ (Preguntas Frecuentes)

**P: ¿Los datos se envían a servidores externos?**
R: No. Todos tus datos financieros se almacenan localmente. Solo se consultan APIs para obtener tipos de cambio actualizados.

**P: ¿Puedo usar la aplicación sin conexión a internet?**
R: Sí, la funcionalidad básica está disponible offline. Solo necesitas internet para obtener tipos de cambio actualizados.

**P: ¿Cómo hago respaldo de mis datos?**
R: Los datos se guardan en localStorage del navegador. Para respaldos permanentes, configura una base de datos según las instrucciones de instalación.

**P: ¿Puedo añadir más monedas?**
R: Actualmente soporta COP y USD. El soporte para más monedas está planificado para futuras versiones.

**P: ¿Es seguro usar esta aplicación para mis finanzas?**
R: Sí, para uso personal. La aplicación no transmite datos financieros y está diseñada siguiendo buenas prácticas de seguridad.

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/control-gastos-cop-usd/issues)
- **Documentación**: [Wiki del Proyecto](https://github.com/tu-usuario/control-gastos-cop-usd/wiki)
- **Email**: tu-email@dominio.com

## 🙏 Agradecimientos

- [Exchange Rates API](https://exchangerate-api.com/) por los tipos de cambio
- [Chart.js](https://www.chartjs.org/) por las visualizaciones
- [Bootstrap](https://getbootstrap.com/) por el framework CSS
- [Flask](https://flask.palletsprojects.com/) por el excelente framework web

## 📊 Estadísticas del Proyecto

![GitHub stars](https://img.shields.io/github/stars/tu-usuario/control-gastos-cop-usd)
![GitHub forks](https://img.shields.io/github/forks/tu-usuario/control-gastos-cop-usd)
![GitHub issues](https://img.shields.io/github/issues/tu-usuario/control-gastos-cop-usd)
![GitHub pull requests](https://img.shields.io/github/issues-pr/tu-usuario/control-gastos-cop-usd)

## 📝 Changelog

### [1.0.0] - 2025-06-21
#### Añadido
- Soporte inicial para COP y USD
- Interfaz web responsiva
- Funcionalidad PWA
- Gráficos de gastos por categoría
- Análisis de impacto del tipo de cambio
- Almacenamiento local de datos

#### Funcionalidades
- Registro de ingresos y gastos
- Conversión automática de moneda
- Dashboard con resumen financiero
- Filtros de historial de transacciones
- Reportes mensuales y tendencias

## 📄 Licencia

Copyright © 2025 [Tu Nombre Completo]

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

### Términos de Uso

- ✅ **Uso comercial permitido**
- ✅ **Modificación permitida**
- ✅ **Distribución permitida**
- ✅ **Uso privado permitido**
- ❗ **Se requiere atribución**
- ❗ **Sin garantía**

---

**Desarrollado con ❤️ para la comunidad financiera colombiana**

*¿Te gusta este proyecto? ¡Dale una ⭐ en GitHub y compártelo con tus amigos!*