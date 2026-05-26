# Proyecto FHIR — Salud Digital

Sistema de gestion de historias clinicas digitales con estandar HL7 FHIR R4. Incluye analisis de riesgo por ML/DL, imagenes medicas en MinIO, y panel de administracion con audit log.

## Arquitectura

```
nginx (80)  -->  frontend (React SPA)
            -->  backend (FastAPI :8000)
                    |-> PostgreSQL (datos clinicos)
                    |-> MinIO (imagenes medicas)
                    |-> ml-service (ONNX tabular :8001)
                    |-> dl-service (ONNX imagen :8002)
                    |-> orchestrator (cola :8003)
```

**Stack:** FastAPI · React · PostgreSQL · MinIO · Nginx · Docker Compose · ONNX Runtime

## Requisitos

- Docker & Docker Compose v2
- 4 GB RAM minimo
- Puerto 80 disponible

## Instalacion rapida

```bash
git clone https://github.com/jfgarzonv/proyecto-fhir-salud-digital.git
cd proyecto-fhir-salud-digital

# Copiar y configurar variables de entorno
cp .env.example .env
nano .env  # editar con valores reales

# Levantar todo
docker compose up -d --build

# Ejecutar seed (crea usuarios, pacientes, observaciones, imagenes)
docker compose exec backend python seed_db.py
```

## Credenciales de prueba

| Rol | Email | Contrasena |
|-----|-------|------------|
| Admin | admin@clinica.com | Admin2026! |
| Medico 1 | medico1@clinica.com | Medico2026! |
| Paciente | paciente@clinica.com | Paciente2026! |

**API Keys:**
- `X-Access-Key: master-access-key`
- `X-Permission-Key: admin-permission | medico-permission | paciente-permission`

## Funcionalidades

### Backend (FastAPI)
- **FHIR R4**: Patient, Observation, Media (imagen), RiskAssessment
- **RBAC**: 3 roles (admin, medico, paciente) con validacion en backend
- **Doble API-Key**: X-Access-Key + X-Permission-Key
- **Cifrado AES-256**: Datos sensibles cifrados en reposo (Fernet)
- **Soft-delete**: Todas las entidades usan `deleted_at` (no DELETE real)
- **Habeas Data**: Consentimiento registrado en BD con timestamp
- **Audit Log**: 19 tipos de evento (LOGIN, LOGOUT, CRUD, INFERENCE, SIGN, etc.)
- **Paginacion**: `?limit=N&offset=M` en todas las listas
- **Rate-limiting**: Nginx con 3 zonas (general, API, login)

### Frontend (React SPA)
- Login animado con validacion
- Modal Habeas Data en primer acceso
- Dashboard con estadisticas
- Lista paginada de pacientes
- Ficha clinica completa con tabs: Observaciones, Reportes, Imagenes, ML, DL
- Visualizacion SHAP (grafica de barras)
- Visor imagen: original vs Grad-CAM lado a lado
- Firma de RiskReport con justificacion al rechazar
- Panel Admin con gestion de usuarios y audit log expandible

### ML Tabular (ml-service)
- Modelo basado en dataset PIMA Diabetes
- Formato ONNX para inferencia CPU-only
- SHAP values calculados por feature
- RiskAssessment FHIR generado automaticamente

### DL Imagen (dl-service)
- Clasificacion de imagenes medicas (retinopatia diabetica)
- Formato ONNX INT8 para CPU
- Grad-CAM generado y almacenado en MinIO
- DiagnosticReport FHIR

### Orquestador
- Cola de inferencia con estados: PENDING -> RUNNING -> DONE/ERROR
- Semaphore(4) para concurrencia controlada
- Polling HTTP desde el frontend

## Metricas del modelo ML (PIMA Diabetes)

El modelo de prediccion de riesgo de diabetes tipo 2 fue entrenado con el dataset **PIMA Indians Diabetes** (768 muestras, 8 features).

| Metrica | Valor |
|---------|-------|
| **Accuracy** | 0.78 |
| **F1-Score (macro)** | 0.75 |
| **AUC-ROC** | 0.83 |
| **Precision (positiva)** | 0.72 |
| **Recall (positiva)** | 0.61 |

**Features utilizados:**
1. Pregnancies (numero de embarazos)
2. Glucose (glucosa plasmatica, LOINC 2339-0)
3. BloodPressure (presion diastolica, LOINC 55284-4)
4. SkinThickness (grosor pliegue cutaneo)
5. Insulin (insulina serica, LOINC 14749-6)
6. BMI (indice de masa corporal, LOINC 39156-5)
7. DiabetesPedigreeFunction (funcion pedigri)
8. Age (edad, LOINC 30525-0)

**Calibracion:** CalibratedClassifierCV con metodo isotonic para probabilidades calibradas.

**Exportacion:** Modelo exportado a formato ONNX con cuantizacion para inferencia eficiente en CPU (~0.5s por prediccion).

## Metricas del modelo DL (Retinopatia Diabetica)

Modelo de clasificacion de imagenes de fondo de ojo para deteccion de retinopatia diabetica.

| Metrica | Valor |
|---------|-------|
| **Accuracy** | 0.73 |
| **F1-Score (macro)** | 0.68 |
| **AUC-ROC** | 0.79 |
| **Quadratic Kappa** | 0.71 |

**Dataset:** APTOS 2019 Blindness Detection (3,662 imagenes de fondo de retina).

**Exportacion:** ONNX INT8 cuantizado para inferencia CPU-only (~3s por imagen).

## Seguridad

- **Rate-limiting**: 60 req/s general, 10 req/min login
- **Headers HTTP**: X-Frame-Options, CSP, X-XSS-Protection, Referrer-Policy
- **Cifrado en reposo**: AES-256 para campos sensibles
- **Cifrado MinIO keys**: Fernet encryption en BD
- **Soft-delete**: No se eliminan datos, se marcan con timestamp
- **Audit log**: 19+ tipos de evento registrados
- **Habeas Data**: Ley 1581/2012 — consentimiento con timestamp

## Estructura del proyecto

```
proyecto-fhir-salud-digital/
├── docker-compose.yml
├── .env.example
├── nginx/nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── models.py
│   ├── routers/ (auth, patients, observations, admin, images, inference)
│   ├── seed_db.py
│   └── minio_client.py
├── frontend/
│   ├── Dockerfile
│   ├── src/pages/ (Login, Dashboard, Patients, PatientDetail, Admin...)
│   └── src/services/api.js
├── ml-service/
│   ├── Dockerfile
│   ├── app.py
│   └── models/
├── dl-service/
│   ├── Dockerfile
│   ├── app.py
│   └── models/
└── orchestrator/
    ├── Dockerfile
    └── orchestrator.py
```

Jeny Valeria Portilla R, Laura Ramirez
- Universidad Autonoma de Occidente — Salud Digital 2026-1
