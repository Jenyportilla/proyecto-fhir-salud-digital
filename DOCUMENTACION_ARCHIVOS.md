# Documentacion de Archivos — Proyecto FHIR Salud Digital

Este documento describe el proposito y la funcionalidad de cada archivo relevante del proyecto, tanto del **backend** (Python/FastAPI) como del **frontend** (React/Vite).

---

## BACKEND (Python + FastAPI)

### Archivos principales (.py)

---

#### `main.py`
**Proposito:** Punto de entrada de la aplicacion backend.

Este archivo crea e inicializa la aplicacion FastAPI. Configura:
- **CORS** (Cross-Origin Resource Sharing) para permitir la comunicacion entre el frontend y el backend.
- **Rate Limiter** (SlowAPI) como proteccion anti-DoS, limitando la cantidad de solicitudes por IP.
- **Creacion de tablas** en la base de datos PostgreSQL usando SQLAlchemy (`Base.metadata.create_all`).
- **Registro de routers** (modulos de rutas): autenticacion, pacientes, observaciones y administracion.
- **Endpoints de salud**: `GET /` (mensaje de bienvenida) y `GET /health` (verificacion de estado del servidor).

---

#### `database.py`
**Proposito:** Configuracion de la conexion a la base de datos PostgreSQL.

Este archivo:
- Lee la variable de entorno `DATABASE_URL` desde el archivo `.env`.
- Corrige el prefijo de la URL si proviene de Render (`postgres://` a `postgresql://`), ya que SQLAlchemy requiere el formato largo.
- Crea el **engine** (motor) de SQLAlchemy con `pool_pre_ping=True` para verificar conexiones antes de usarlas.
- Define `SessionLocal` como la fabrica de sesiones de base de datos.
- Expone la funcion `get_db()`, que es un generador usado como **dependencia de FastAPI** para inyectar sesiones de BD en los endpoints. Abre la sesion, la entrega al endpoint y la cierra al finalizar.

---

#### `models.py`
**Proposito:** Definicion de todos los modelos (tablas) de la base de datos usando SQLAlchemy ORM.

Define 8 tablas/modelos:

| Modelo | Tabla | Descripcion |
|--------|-------|-------------|
| `User` | `users` | Usuarios del sistema (admin, medico, paciente). Incluye email, password hasheado, nombre, cedula, rol, estado activo, aceptacion de Habeas Data y soft-delete. |
| `Patient` | `patients` | Pacientes clinicos (recurso FHIR Patient). Almacena nombre, fecha nacimiento, genero, documento de identidad (encriptado), resumen medico, doctor asignado y estado. |
| `Observation` | `observations` | Observaciones clinicas (recurso FHIR Observation). Guarda codigo LOINC, nombre legible, valor numerico, unidad UCUM y fecha efectiva. |
| `RiskReport` | `risk_reports` | Reportes de riesgo (recurso FHIR RiskAssessment). Contiene puntaje de riesgo, categoria, predicciones del modelo ML/DL, valores SHAP, URL Grad-CAM, firma del medico y notas clinicas. |
| `Consent` | `consent` | Consentimientos (Habeas Data / FHIR Consent). Registra tipo de consentimiento, version, aceptacion, IP y recurso FHIR. |
| `InferenceQueue` | `inference_queue` | Cola de inferencia para el orquestador ML/DL. Almacena ID de tarea, tipo de modelo, estado (PENDING, RUNNING, DONE, ERROR) y resultado. |
| `AuditLog` | `audit_log` | Registro de auditoria (INSERT-ONLY, nunca se modifica ni elimina). Registra acciones como LOGIN, VIEW_PATIENT, CREATE_OBSERVATION, etc. |
| `ModelFeedback` | `model_feedback` | Feedback del medico sobre reportes de riesgo. El medico puede ACCEPT o REJECT un reporte con justificacion. |

Todos los modelos (excepto `AuditLog`) implementan **soft-delete** mediante el campo `deleted_at`.

---

#### `schemas.py`
**Proposito:** Esquemas de validacion de datos de entrada/salida usando Pydantic.

Define los modelos Pydantic que validan:
- **Auth**: `LoginRequest` (email + password), `LoginResponse` (token JWT + datos del usuario), `HabeasDataRequest`.
- **Users**: `UserCreate` (con validaciones de email, password minimo 6 chars, cedula), `UserResponse`, `UserUpdate`.
- **Patients**: `PatientCreate`, `PatientResponse`, `PatientUpdate`.
- **Observations**: `ObservationCreate` (con codigo LOINC obligatorio, valor numerico, unidad UCUM), `ObservationResponse`.
- **Risk Reports**: `RiskReportResponse`, `SignReportRequest`.
- **Inference**: `InferenceRequest`, `InferenceResponse`, `InferenceStatusResponse`.
- **Feedback**: `FeedbackCreate` (ACCEPT/REJECT con justificacion).
- **Audit Log**: `AuditLogResponse`.
- **Paginacion**: `PaginatedResponse` (total, limit, offset, data).

Estos esquemas aseguran que los datos enviados al backend cumplan con el formato y las reglas de validacion definidas.

---

#### `auth.py`
**Proposito:** Modulo de autenticacion, autorizacion y auditoria.

Implementa cuatro capas de seguridad:

1. **Hashing de passwords**: Usa bcrypt con work factor 12 para hashear y verificar contrasenas.
2. **JWT Tokens**: Genera tokens de acceso con expiracion de 8 horas usando el algoritmo HS256. Incluye funciones `create_access_token()` y `decode_token()`.
3. **Doble API-Key**: Funcion `validate_api_keys()` que verifica dos headers HTTP en cada peticion:
   - `X-Access-Key`: Clave de acceso general.
   - `X-Permission-Key`: Clave de permiso que mapea al rol del usuario (admin, medico, paciente).
4. **RBAC (Control de Acceso Basado en Roles)**: Decoradores de dependencia de FastAPI:
   - `get_current_user()`: Extrae el usuario del JWT Bearer token.
   - `require_admin()`: Restringe acceso solo a administradores.
   - `require_medico()`: Restringe acceso solo a medicos.
   - `require_medico_or_admin()`: Permite acceso a medicos y administradores.
5. **Audit Log**: Funcion `log_audit()` que registra cada accion en la tabla `audit_log` (INSERT-ONLY).

---

#### `seed_db.py`
**Proposito:** Script para poblar la base de datos con datos de prueba.

Se ejecuta manualmente con `python seed_db.py`. Realiza:
- Crea todas las tablas en la base de datos si no existen.
- Si ya hay datos, pregunta si desea reiniciar (limpia todo).
- Crea **4 usuarios** de prueba:
  - 1 Admin (`admin@clinica.com` / `Admin2026!`)
  - 2 Medicos (`medico1@clinica.com`, `medico2@clinica.com` / `Medico2026!`)
  - 1 Paciente (`paciente@clinica.com` / `Paciente2026!`)
- Crea **31 pacientes** de prueba con datos colombianos realistas (nombres, cedulas, fechas de nacimiento).
- Crea **180 observaciones** clinicas para los primeros 10 pacientes, usando 6 codigos LOINC diferentes: Glucosa, Presion Arterial, BMI, Insulina, Temperatura y Frecuencia Cardiaca.

---

#### `setup_db.py`
**Proposito:** Script para crear la base de datos PostgreSQL automaticamente.

Se ejecuta **antes** del `seed_db.py`. Realiza:
- Lee la URL de conexion desde el archivo `.env`.
- Parsea los componentes de la URL (usuario, password, host, puerto, nombre de BD).
- Se conecta a la base de datos `postgres` (que siempre existe) y verifica si la base de datos del proyecto ya existe.
- Si no existe, la crea con `CREATE DATABASE`.
- Verifica que la conexion funcione correctamente.
- Proporciona mensajes de error detallados y soluciones para problemas comunes: contrasena incorrecta, PostgreSQL no esta corriendo, usuario no existe, etc.

---

### Archivos de routers (`backend/routers/`)

---

#### `routers/auth_router.py`
**Proposito:** Endpoints de autenticacion y consentimiento.

Endpoints:
| Metodo | Ruta | Funcion |
|--------|------|---------|
| `POST` | `/auth/login` | Login con doble API-Key + email/password. Devuelve JWT. |
| `POST` | `/auth/habeas-data` | Registra aceptacion del consentimiento de Habeas Data (Ley 1581/2012). Crea un recurso FHIR Consent en la BD. |
| `GET` | `/auth/me` | Retorna los datos del usuario autenticado actualmente. |

---

#### `routers/patients.py`
**Proposito:** CRUD completo de pacientes con RBAC y soft-delete.

Endpoints:
| Metodo | Ruta | Funcion | Permiso |
|--------|------|---------|---------|
| `GET` | `/fhir/Patient` | Lista paginada de pacientes. Admin ve todos, medico ve sus asignados, paciente ve solo el propio. | Todos |
| `GET` | `/fhir/Patient/{id}` | Detalle de un paciente especifico. | Todos (con RBAC) |
| `POST` | `/fhir/Patient` | Crear nuevo paciente. | Medico, Admin |
| `PATCH` | `/fhir/Patient/{id}` | Actualizar datos de un paciente. | Medico, Admin |
| `DELETE` | `/fhir/Patient/{id}` | Soft-delete de paciente. | Solo Admin |
| `PATCH` | `/fhir/Patient/{id}/restore` | Restaurar paciente eliminado. | Solo Admin |
| `GET` | `/fhir/Patient/{id}/can-close` | Verificar si el paciente puede cerrarse (no debe tener RiskReports sin firma). | Medico, Admin |
| `GET` | `/fhir/Patient/doctors` | Lista de medicos activos para asignacion. | Medico, Admin |

---

#### `routers/observations.py`
**Proposito:** CRUD de observaciones clinicas con codigos LOINC y deteccion de outliers.

Endpoints:
| Metodo | Ruta | Funcion | Permiso |
|--------|------|---------|---------|
| `GET` | `/fhir/Observation` | Lista paginada de observaciones con filtro por paciente y RBAC. | Todos |
| `POST` | `/fhir/Observation` | Crear observacion con codigo LOINC. Auto-completa el display name. Verifica outliers. | Medico, Admin |
| `PATCH` | `/fhir/Observation/{id}` | Actualizar observacion existente. | Medico, Admin |
| `DELETE` | `/fhir/Observation/{id}` | Soft-delete de observacion. | Solo Admin |
| `GET` | `/fhir/Observation/outliers` | Detectar valores fuera de rango clinico en todas las observaciones. | Medico, Admin |

Incluye un diccionario de **codigos LOINC validos** y **rangos de outliers** para Temperatura, Frecuencia Cardiaca, Presion Arterial y Glucosa.

---

#### `routers/admin.py`
**Proposito:** Panel de administracion: gestion de usuarios, audit log y estadisticas.

Endpoints:
| Metodo | Ruta | Funcion | Permiso |
|--------|------|---------|---------|
| `GET` | `/admin/users` | Lista paginada de todos los usuarios. | Solo Admin |
| `POST` | `/admin/users` | Crear nuevo usuario. Valida email y cedula duplicados. | Solo Admin |
| `PATCH` | `/admin/users/{id}` | Actualizar datos de un usuario. | Solo Admin |
| `DELETE` | `/admin/users/{id}` | Soft-delete de usuario (no puede eliminarse a si mismo). | Solo Admin |
| `GET` | `/admin/doctors` | Lista de medicos activos para asignacion. | Solo Admin |
| `GET` | `/admin/audit-log` | Consulta del registro de auditoria con filtro por accion. | Solo Admin |
| `GET` | `/admin/stats` | Estadisticas generales: conteos de usuarios, pacientes, observaciones, reportes de riesgo y entradas de auditoria. | Solo Admin |

---

### Archivo SQL

---

#### `seed_users.sql`
**Proposito:** Archivo de referencia con las credenciales de prueba y queries SQL utiles.

**No se ejecuta directamente.** Es un documento de consulta que contiene:
- Tabla con todas las credenciales de prueba (email, contrasena, API Keys por rol).
- Sentencias `INSERT INTO` con passwords hasheados en bcrypt (como alternativa manual al script `seed_db.py`).
- Queries utiles para consultar usuarios y audit log directamente en PostgreSQL.

---
---

## FRONTEND (React + Vite)

### Archivo raiz

---

#### `App.jsx`
**Proposito:** Componente raiz de la aplicacion React. Define el sistema de rutas y la proteccion de acceso.

Configuracion:
- Usa `BrowserRouter` de React Router para navegacion SPA.
- Envuelve toda la app en `AuthProvider` (contexto de autenticacion global).
- Define el componente `ProtectedRoute` que:
  - Redirige a `/login` si el usuario no esta autenticado.
  - Redirige a `/dashboard` si el usuario no tiene el rol requerido.
  - Muestra un spinner de carga mientras verifica la sesion.

Rutas definidas:
| Ruta | Componente | Acceso |
|------|-----------|--------|
| `/login` | Login | Publico (redirige a dashboard si ya hay sesion) |
| `/dashboard` | Dashboard | Todos los roles |
| `/patients` | Patients | Todos los roles |
| `/observations` | Observations | Admin, Medico |
| `/alerts` | Alerts | Admin, Medico |
| `/admin` | Admin | Solo Admin |

---

### Services (`frontend/src/services/`)

---

#### `api.js`
**Proposito:** Servicio HTTP centralizado para la comunicacion con el backend.

Crea una instancia de Axios con:
- **Base URL** configurable via variable de entorno `VITE_API_URL` (por defecto `http://localhost:8000`).
- **Timeout** de 30 segundos.
- **Interceptor de request**: Inyecta automaticamente en cada peticion:
  - Token JWT (`Authorization: Bearer ...`) desde localStorage.
  - `X-Access-Key` y `X-Permission-Key` (API Keys de doble autenticacion).
- **Interceptor de response**: Si el backend responde con estado 401 (no autorizado), limpia localStorage y redirige al login.

Exporta 4 modulos de API organizados por recurso:
- `authAPI`: login, me, habeasData.
- `patientsAPI`: list, get, create, update, delete, restore, canClose, doctors.
- `observationsAPI`: list, create, update, delete, outliers.
- `adminAPI`: users, createUser, updateUser, deleteUser, auditLog, stats.

---

### Components (`frontend/src/components/`)

---

#### `Layout.jsx`
**Proposito:** Componente de layout principal que estructura la interfaz de la aplicacion.

Implementa:
- **Sidebar (barra lateral izquierda)** con:
  - Logo y titulo "FHIR Salud Digital".
  - Menu de navegacion con iconos SVG. Los items se muestran u ocultan segun el rol del usuario:
    - Dashboard: todos los roles.
    - Pacientes: todos los roles.
    - Observaciones: admin y medico.
    - Alertas: admin y medico.
    - Admin: solo admin.
  - Pie del sidebar con informacion del usuario: avatar con inicial del nombre, nombre completo, badge de rol con color diferenciado (rojo para admin, azul para medico, verde para paciente), y boton "Cerrar Sesion".
- **Area principal (main-content)**: Renderiza el contenido de la ruta activa usando `<Outlet />` de React Router.
- **Footer**: Texto legal "Protegido bajo Ley 1581/2012 | Datos cifrados AES-256 | Sistema auditado".

#### `Layout.css`
**Proposito:** Estilos del componente Layout.

Define:
- Estructura CSS Grid de dos columnas (sidebar de 260px + area principal flexible).
- Estilos del sidebar: fondo oscuro con gradiente (`#0a0e1a` a `#111827`), bordes con separadores sutiles, altura completa del viewport.
- Estilos de navegacion: links con iconos, estados hover con fondo semitransparente, estado activo con fondo de acento y borde izquierdo.
- Estilos del usuario en el footer: avatar circular con gradiente, badges de rol con colores diferenciados.
- Boton de logout con estilo secundario.
- Area principal con padding, scroll vertical y fondo predeterminado.
- Footer fijo en la parte inferior con texto legal.

---

### Pages (`frontend/src/pages/`)

---

#### `Login.jsx`
**Proposito:** Pantalla de inicio de sesion.

Implementa:
- Formulario con campos de email y contrasena.
- Valores de API Keys (X-Access-Key y X-Permission-Key) preconfigurados y ocultos del diseno (se mantiene la logica internamente).
- Al enviar el formulario:
  1. Guarda las API Keys en localStorage.
  2. Llama a `login()` del contexto de autenticacion.
  3. Si el usuario no ha aceptado Habeas Data, muestra el modal de consentimiento.
  4. Si ya lo acepto, redirige al Dashboard.
- **Modal de Habeas Data**: Informa al usuario sobre la Ley 1581/2012 y el Decreto 1377/2013. Requiere aceptacion obligatoria para continuar.

#### `Login.css`
**Proposito:** Estilos de la pantalla de login.

Define:
- Fondo oscuro (`#0a0e1a`) con efectos de orbes animados (esferas de color con blur que se mueven suavemente).
- Contenedor del formulario con efecto glassmorphism (fondo semitransparente, blur, borde sutil).
- Logo con caja de icono con gradiente.
- Campos de entrada con fondo oscuro, bordes sutiles y transicion de color en focus.
- Boton principal con gradiente azul y efecto hover.
- Estilos del modal de Habeas Data: overlay oscuro con el formulario centrado.
- Animacion `fade-in` para la aparicion suave del formulario.

---

#### `Dashboard.jsx`
**Proposito:** Pantalla principal del sistema tras el login.

Muestra:
- Mensaje de bienvenida personalizado con el nombre del usuario.
- Si el usuario es **admin**, carga y muestra las estadisticas del sistema:
  - Total de pacientes activos.
  - Total de observaciones registradas.
  - Total de usuarios del sistema.
  - Entries del log de auditoria.
- Para todos los roles: Muestra los ultimos 5 pacientes registrados en una tabla con nombre, genero, estado y fecha de creacion.
- Tarjeta informativa sobre cumplimiento legal (Ley 1581/2012).

#### `Dashboard.css`
**Proposito:** Estilos de la pantalla Dashboard.

Define:
- Grid de tarjetas de estadisticas (4 columnas responsivas) con fondo de gradiente oscuro.
- Tabla de pacientes recientes con filas alternadas y efecto hover.
- Tarjeta de informacion legal con borde izquierdo de color de acento.
- Animaciones de entrada (fade-in con desplazamiento vertical).
- Diseno responsivo que adapta el grid a 2 columnas en pantallas medianas y 1 columna en moviles.

---

#### `Patients.jsx`
**Proposito:** Pantalla de gestion de pacientes (CRUD completo).

Funcionalidades:
- **Lista paginada** de pacientes con barra de busqueda por nombre/cedula.
- **Crear paciente**: Modal con formulario para nombre, cedula, fecha de nacimiento, genero, medico asignado y resumen medico.
- **Editar paciente**: Mismo modal pre-cargado con los datos actuales.
- **Eliminar paciente**: Confirmacion antes de ejecutar soft-delete (solo Admin).
- **Ver detalle**: Navegacion a la pantalla `PatientDetail` al hacer clic en un paciente.
- **Selector de medico**: Carga dinamicamente la lista de medicos disponibles para asignacion.
- Paginacion con botones "Anterior" y "Siguiente".
- Control de acceso: solo Admin y Medico ven los botones de crear/editar/eliminar.

#### `Patients.css`
**Proposito:** Estilos de la pantalla de Pacientes.

Define:
- Toolbar con barra de busqueda y boton de crear paciente.
- Tabla de pacientes con columnas para nombre, cedula, genero, doctor asignado, estado y acciones.
- Badges de genero y estado con colores diferenciados.
- Botones de accion (editar, eliminar) con iconos.
- Modal de formulario con fondo overlay oscuro.
- Controles de paginacion.
- Diseno responsivo.

---

#### `PatientDetail.jsx`
**Proposito:** Pantalla de detalle de un paciente individual.

Muestra:
- Informacion completa del paciente: nombre, cedula, fecha de nacimiento, genero, estado, medico asignado.
- **Tabla de observaciones** del paciente con: codigo LOINC, nombre, valor, unidad y fecha.
- Indicadores de outliers (valores fuera de rango clinico se resaltan con badge de alerta).
- Boton para regresar a la lista de pacientes.

#### `PatientDetail.css`
**Proposito:** Estilos de la pantalla de detalle de paciente.

Define:
- Tarjeta de informacion del paciente con grid de campos.
- Tabla de observaciones con resaltado de outliers.
- Badge de alerta para valores fuera de rango.
- Boton de retorno con icono de flecha.
- Diseno responsivo.

---

#### `Observations.jsx`
**Proposito:** Pantalla de gestion de observaciones clinicas (CRUD con LOINC).

Funcionalidades:
- **Lista paginada** de observaciones con filtro por paciente.
- **Selector de paciente**: Dropdown que carga todos los pacientes disponibles.
- **Crear observacion**: Modal con formulario para seleccionar paciente, codigo LOINC (dropdown con codigos predefinidos), valor numerico y unidad.
- **Editar observacion**: Modal pre-cargado con los datos actuales.
- **Eliminar observacion**: Confirmacion antes de ejecutar soft-delete.
- **Codigos LOINC disponibles**: Glucosa (2339-0), Presion Arterial (55284-4), BMI (39156-5), Insulina (14749-6), Temperatura (8310-5), Frecuencia Cardiaca (8867-4), Glucosa Serum (2345-7), Hemoglobina (718-7), Creatinina (2160-0), Leucocitos (6690-2).
- Auto-completa la unidad de medida segun el codigo LOINC seleccionado.
- Indicadores de outliers en la lista.
- Paginacion.

#### `Observations.css`
**Proposito:** Estilos de la pantalla de Observaciones.

Define:
- Filtro de paciente como barra superior.
- Tabla de observaciones con columnas para paciente, codigo LOINC, nombre, valor, unidad e indicador de outlier.
- Badge de outlier con color de alerta (rojo/naranja).
- Modal de formulario para crear/editar observaciones.
- Controles de paginacion.

---

#### `Alerts.jsx`
**Proposito:** Pantalla de alertas clinicas (deteccion de outliers).

Funcionalidades:
- Carga automaticamente todas las observaciones con valores fuera de rango clinico desde el endpoint `/fhir/Observation/outliers`.
- Muestra una tabla con: ID del paciente, codigo LOINC, nombre del valor, valor registrado, unidad, y rango esperado (min-max).
- Si no hay outliers, muestra un mensaje indicando que todos los valores estan dentro de los rangos normales.
- Accesible solo para Admin y Medico.

#### `Alerts.css`
**Proposito:** Estilos de la pantalla de Alertas.

Define:
- Tabla de outliers con fondo de alerta.
- Celdas de rango con formato visual diferenciado.
- Mensaje vacio centrado cuando no hay alertas.
- Diseno responsivo.

---

#### `Admin.jsx`
**Proposito:** Panel de administracion de usuarios y audit log (solo Admin).

Funcionalidades organizadas en **3 pestanas**:

1. **Usuarios**: CRUD completo de usuarios del sistema.
   - Lista con nombre, cedula, email, rol, estado activo.
   - Crear usuario: formulario con nombre, cedula, email, contrasena, rol.
   - Editar usuario: modificar nombre, cedula, rol, estado activo.
   - Eliminar usuario: soft-delete con confirmacion (no puede eliminarse a si mismo).

2. **Audit Log**: Registro de auditoria del sistema.
   - Tabla con usuario, accion, recurso, estado, IP y timestamp.
   - Filtro por tipo de accion.
   - Paginacion.

3. **Estadisticas**: Metricas generales del sistema.
   - Tarjetas con conteos de: usuarios totales (desglose por rol), pacientes (total y activos), observaciones, reportes de riesgo (total y pendientes de firma), entradas del audit log.

#### `Admin.css`
**Proposito:** Estilos del panel de administracion.

Define:
- Sistema de pestanas (tabs) con estados activo/inactivo.
- Tablas de usuarios y audit log.
- Badges de rol y estado con colores diferenciados.
- Botones de accion en las filas.
- Modal de formulario para crear/editar usuarios.
- Grid de tarjetas de estadisticas.

---

## Resumen de la Arquitectura

```
proyecto-fhir-salud-digital/
├── backend/
│   ├── main.py              ← Entrada: crea app FastAPI, middleware, routers
│   ├── database.py          ← Conexion PostgreSQL con SQLAlchemy
│   ├── models.py            ← 8 tablas: User, Patient, Observation, etc.
│   ├── schemas.py           ← Validacion Pydantic de entrada/salida
│   ├── auth.py              ← JWT + API Keys + RBAC + Audit Log
│   ├── setup_db.py          ← Script: crear la base de datos
│   ├── seed_db.py           ← Script: poblar con datos de prueba
│   ├── seed_users.sql       ← Referencia: credenciales y queries SQL
│   └── routers/
│       ├── auth_router.py   ← Login, Habeas Data, /me
│       ├── patients.py      ← CRUD Pacientes + RBAC
│       ├── observations.py  ← CRUD Observaciones + LOINC + Outliers
│       └── admin.py         ← Usuarios, Audit Log, Estadisticas
│
└── frontend/src/
    ├── App.jsx              ← Rutas protegidas + AuthProvider
    ├── services/
    │   └── api.js           ← Axios centralizado con interceptors
    ├── components/
    │   ├── Layout.jsx       ← Sidebar + navegacion + footer
    │   └── Layout.css       ← Estilos del layout
    └── pages/
        ├── Login.jsx/css    ← Pantalla de login + Habeas Data
        ├── Dashboard.jsx/css← Panel principal con estadisticas
        ├── Patients.jsx/css ← CRUD de pacientes
        ├── PatientDetail.jsx/css ← Detalle de paciente + observaciones
        ├── Observations.jsx/css  ← CRUD de observaciones LOINC
        ├── Alerts.jsx/css   ← Deteccion de outliers clinicos
        └── Admin.jsx/css    ← Gestion usuarios + audit log + stats
```
