# DOCUMENTACIÓN TÉCNICA ESTRUCTURADA - GESTIÓN DE BIBLIOTECA

Este documento proporciona una referencia exhaustiva de todos los módulos de código del sistema, incluyendo modelos de base de datos, lógica de control, aplicaciones, servicios y automatización.

---

# MÓDULO: CONFIGURACIÓN GLOBAL
**Archivo:** `blb_django/settings.py`
Es el cerebro del proyecto. Aquí se definen todas las reglas de infraestructura.

*   **INSTALLED_APPS (Líneas 37-45):** Registra los módulos activos. Se añadió `'gestion'` para que Django reconozca nuestros modelos.
*   **DATABASES (Líneas 80-85):** Configurado con SQLite3 para simplicidad y portabilidad.
*   **LANGUAGE_CODE (Línea 110):** Seteado en `es-ES` para que los errores y fechas de Django salgan en español.
*   **EMAIL CONFIG (Líneas 133-144):** 
    *   **EMAIL_BACKEND:** Actualmente en modo `console`, lo que permite que los correos del Cron se vean en la terminal sin necesidad de un servidor real (ideal para desarrollo).
*   **LOGIN_REDIRECT_URL (Línea 130):** Define que tras loguearse, el usuario siempre vaya al Dashboard.

---

# MÓDULO: GESTIÓN (APP PRINCIPAL)

## 1. Módulo: Modelos de Base de Datos
**Archivo:** `gestion/models.py`
Define la estructura de datos y lógica de negocio.

### A. Clase `Prestamos` (Líneas 52-155) - CRÍTICA
*   **confirmar() (Líneas 84-92):** Activa el préstamo y calcula automáticamente **7 días** de plazo (Línea 91).
*   **finalizar() (Líneas 94-124):** 
    *   **Lógica Excluyente:** Si es Pérdida ('p'), cobra el valor y termina (Líneas 113-115).
    *   **Lógica Acumulativa:** Si es Daño ('d'), cobra el daño Y verifica retraso acumulando multas (Líneas 118-124).

---

## 2. Módulo: Vistas (Lógica de Control)
**Archivo:** `gestion/views.py`

*   **crear_prestamo (Líneas 183-235):** [CRÍTICO] Implementa el **Bloqueo de Morosos**. Verifica multas impagas y estados vencidos antes de permitir un nuevo préstamo.
*   **index (Líneas 14-35):** Genera los KPIs (indicadores) para el Dashboard dinámico.

---

## 3. Módulo: Formularios
**Archivo:** `gestion/forms.py`

*   **FormularioRegistroExtendido (Líneas 36-69):** 
    *   **Importancia:** ALTA. 
    *   **Lógica:** Sobreescribe el método `save()` (Línea 57) para guardar datos en el `User` de Django y en nuestro `PerfilUsuario` (DNI, Teléfono) en una sola transacción.

---

## 4. Módulo: Servicios Externos
**Archivo:** `gestion/services.py`

*   **ClienteOpenLibrary (Líneas 3-68):** 
    *   **Función:** Automatiza la búsqueda en internet.
    *   **Lógica Crítica:** Gestiona sesiones con `requests` y formatea las URLs de portadas de libros usando el ID o el ISBN (Líneas 57-67).

---

## 5. Módulo: Pruebas Automáticas (Tests)
**Archivo:** `gestion/tests.py`

*   **TestModelosBiblioteca (Clase):**
    *   **test_prestamo_vencido_genera_multa (Línea 68):** Simula el paso del tiempo para asegurar que el sistema cobre exactamente $0.50 por día de retraso.
    *   **test_prestamo_perdida_excluyente (Línea 94):** Garantiza que no se cobren cargos injustos de retraso si el libro fue reportado como perdido.

---

## 6. Módulo: Aplicación y Señales
**Archivo:** `gestion/apps.py`

*   **GestionConfig (Líneas 4-6):** Configuración básica del nombre de la app.
*   **Nota:** Aquí es donde Django registra internamente la aplicación para que las tablas se creen correctamente en la base de datos.

---

## 7. Módulo: Automatización (Management Commands)
**Directorio:** `gestion/management/commands/verificar_vencimientos.py`

*   **Función:** Actúa como un **CRON JOB** (tarea programada).
*   **Lógica (Líneas 13-53):** 
    1. Filtra préstamos vencidos.
    2. Bloquea al usuario (Estado 'multado').
    3. Envía un correo electrónico automático informando del retraso y la multa.

---

## 8. Módulo: Rutas (URLS)
**Archivo:** `gestion/urls.py`
Mantiene el mapa de navegación, separando la administración de usuarios, libros, préstamos y la integración con la API.
