# 🏥 Proyecto FHIR - Historia Clínica Digital

Sistema de gestión de historias clínicas basado en el estándar FHIR con API REST, base de datos PostgreSQL y dashboard médico.

## ✨ Características

- 🔐 **Doble autenticación** con API Keys (Access + Permission)
- 👥 **3 roles de usuario**: Admin, Médico, Paciente
- 🗄️ **Base de datos PostgreSQL** en Render (normalizada con FK)
- 🔒 **Encriptación** de datos sensibles (Fernet)
- ⚡ **Rate-Limiting** anti-DoS (5-10 peticiones/min)
- 📊 **Dashboard médico** en Streamlit con gráficas Plotly
- 🚨 **Alertas de outliers** (valores clínicos imposibles)
- 📄 **Paginación** de resultados (limit & offset)
- 🌐 **API REST** siguiendo estándar FHIR-Lite

## 📦 Requisitos

- Python 3.8+
- PostgreSQL 12+
- Git

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO