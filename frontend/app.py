# Es el archivo principal del frontend (Dashboard). Es la interfaz gráfica

import streamlit as st
import requests
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Dashboard Clínico", layout="wide")
st.title("🏥 Dashboard Clínico - Historia FHIR")

# --- LOGIN DE SEGURIDAD
st.sidebar.header("🔐 Login")
access_key = st.sidebar.text_input("Access Key", type="password")
permission_key = st.sidebar.text_input("Permission Key", type="password")

role = st.sidebar.selectbox(
    "Rol",
    ["Admin", "Médico", "Paciente/Auditor"]
)

# Inicializar sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.sidebar.button("Ingresar"):
    
    acceso_valido = False
    # Validación por rol
    if role == "Admin" and permission_key == "admin123":
        acceso_valido = True

    elif role == "Médico" and permission_key == "medico123":
        acceso_valido = True

    elif role == "Paciente/Auditor" and permission_key == "paciente123":
        acceso_valido = True


    if acceso_valido:

        st.session_state.logged_in = True
        st.session_state.access_key = access_key
        st.session_state.permission_key = permission_key
        st.session_state.role = role
        st.sidebar.success(f"✅ Acceso autorizado como {role}")
    
    else:
        st.sidebar.error("❌ Contraseña incorrecta para ese rol")

# --- Si no está logueado, mostrar mensaje ---
if not st.session_state.get('logged_in'):
    st.warning("🔒 Por favor inicia sesión con las API Keys")
    st.stop()

# --- Headers para las peticiones ---
headers = {
    "X-Access-Key": st.session_state.access_key,
    "X-Permission-Key": "admin123" 
}

# Esto le pide al backend la lista de pacientes cuando el médico haga clic en consultar paciente
BACKEND_URL = "https://proyecto-fhir-api.onrender.com"

tab1, tab2, tab3 = st.tabs(["👨‍️ Pacientes", " Gráficas", " Alertas"])

with tab1:
    st.header("Lista de Pacientes")
    
    if st.button("Consultar Pacientes"):
        try:
            response = requests.get(f"{BACKEND_URL}/fhir/Patient", headers=headers, timeout=30)
            
            if response.status_code == 200:
                pacientes = response.json()
                
                if pacientes:
                    df_pacientes = pd.DataFrame(pacientes)
                    
                    if st.session_state.role == "Admin":
                        df_admin = df_pacientes[["id"]].copy()
                        df_admin["Datos"] = "🔒 Encriptado"
                        st.dataframe(df_admin, use_container_width=True)
                    elif st.session_state.role == "Médico":
                        # Médico ve toda la información
                        st.dataframe(df_pacientes, use_container_width=True)
                    elif st.session_state.role == "Paciente/Auditor":
                        st.info("🔒 Acceso limitado. Solo puedes ver tu información.")
                        paciente_id = st.selectbox(
                            "Selecciona tu ID de paciente",
                            options=df_pacientes["id"].tolist()
                        )
                        if paciente_id:
                            df_paciente = df_pacientes[df_pacientes["id"] == paciente_id]
                            st.dataframe(df_paciente, use_container_width=True)
                                
                        else:
                            st.info("No hay pacientes registrados")
                    else:
                        st.error(f"❌ Error {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")

with tab2:
    st.header("📈 Tendencias de Signos Vitales")

    st.subheader("Seleccionar paciente")
    response_pacientes = requests.get(f"{BACKEND_URL}/fhir/Patient", headers=headers)
    
    lista_pacientes = {}

    if response_pacientes.status_code == 200:
        pacientes = response_pacientes.json()

        for p in pacientes:
            lista_pacientes[p["id"]] = p["name"]

    paciente_seleccionado = st.selectbox(
        "Paciente",
        options=list(lista_pacientes.keys()),
        format_func=lambda x: lista_pacientes[x]
    )
    
    if st.button("Cargar Observaciones"):
        try:
            response = requests.get(f"{BACKEND_URL}/fhir/Observation", headers=headers)
            
            if response.status_code == 200:
                
                observaciones = response.json()
                
                if observaciones:
                    df_obs = pd.DataFrame(observaciones)
                    
                    # FILTRAR SOLO EL PACIENTE SELECCIONADO
                    df_obs = df_obs[df_obs["patient_id"] == paciente_seleccionado]

                    fig = px.line(df_obs, x="id", y="value", color="type", 
                                  title=f"Tendencias del paciente {lista_pacientes[paciente_seleccionado]}",
                                  labels={"value": "Valor", "type": "Tipo", "id": "ID Obs"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar datos en tabla
                if st.session_state.role == "Médico":
                    st.dataframe(
                        df_obs[["patient_name", "type", "value", "unit"]].rename(
                            columns={"patient_name": "Paciente", "type": "Tipo", "value": "Valor", "unit": "Unidad"}
                        ),
                        use_container_width=True
                    )

                elif st.session_state.role == "Admin":
                    total_obs = len(df_obs)
                    st.metric(
                        label="Total de observaciones del paciente",
                        value=total_obs
                    )
                    st.info("🔒 El administrador no puede ver el contenido de las observaciones.")
                elif st.session_state.role == "Paciente/Auditor":
                    st.warning("🔒 Acceso solo lectura. No puedes ver observaciones clínicas.")
                else:
                    st.info("No hay observaciones registradas")
            else:
                st.error(f"❌ Error {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")
   

with tab3:
    st.header("🚨 Alertas de Valores Imposibles")
    
    if st.button("Verificar Outliers"):
        try:
            response = requests.get(f"{BACKEND_URL}/fhir/Observation", headers=headers, timeout=30)
            
            if response.status_code == 200:
                observaciones = response.json()
                
                if observaciones:
                    outliers = []
                    
                    for obs in observaciones:
                        es_outlier = False
                        razon = ""
                        
                        if obs.get("type") == "temperature" and obs.get("value", 0) > 45:
                            es_outlier = True
                            razon = "🌡️ Temperatura > 45°C (Imposible)"
                        elif obs.get("type") == "heart_rate" and obs.get("value", 0) > 250:
                            es_outlier = True
                            razon = "❤️ Frecuencia cardíaca > 250 lpm (Imposible)"
                        elif obs.get("type") == "blood_pressure" and obs.get("value", 0) > 300:
                            es_outlier = True
                            razon = "🩸 Presión arterial > 300 mmHg (Imposible)"
                        
                        if es_outlier:
                            outliers.append({
                                "ID": obs.get("id"),
                                "Paciente (ID)": obs.get("patient_id"),
                                "Nombre del Paciente": obs.get("patient_name", "Desconocido"),
                                "Tipo": obs.get("type"),
                                "Valor": obs.get("value"),
                                "Unidad": obs.get("unit"),
                                "Alerta": razon
                            })
                    
                    if outliers:
                        st.error(f"⚠️ Se detectaron {len(outliers)} valor(es) imposible(s)")
                        df_outliers = pd.DataFrame(outliers)
                        
                        # Tabla simple sin estilos complejos
                        st.dataframe(
                            df_outliers[["Nombre del Paciente", "Tipo", "Valor", "Unidad", "Alerta"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.success("✅ No se detectaron outliers. Todos los valores son válidos.")
                else:
                    st.info("No hay observaciones para verificar")
            else:
                st.error(f"❌ Error {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            st.warning("💡 El backend puede estar 'dormido'. Espera 30 segundos e intenta de nuevo.")