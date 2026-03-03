import streamlit as st
import requests
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Dashboard Clínico", layout="wide")
st.title("🏥 Dashboard Clínico - Historia FHIR")

# --- LOGIN DE SEGURIDAD (Guía E.1) ---
st.sidebar.header("🔐 Login")
access_key = st.sidebar.text_input("Access Key", type="password")
permission_key = st.sidebar.text_input("Permission Key", type="password")

# Inicializar sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.sidebar.button("Ingresar"):
    if access_key and permission_key:
        st.session_state.logged_in = True
        st.session_state.access_key = access_key
        st.session_state.permission_key = permission_key
        st.sidebar.success("✅ Autenticado")
    else:
        st.sidebar.error("❌ Ingresa ambas claves")

# --- Si no está logueado, mostrar mensaje ---
if not st.session_state.get('logged_in'):
    st.warning("🔒 Por favor inicia sesión con las API Keys")
    st.stop()

# --- Headers para las peticiones ---
headers = {
    "X-Access-Key": st.session_state.access_key,
    "X-Permission-Key": st.session_state.permission_key
}

# URL del backend en Render
BACKEND_URL = "https://proyecto-fhir-api.onrender.com"

# --- Pestañas para organizar ---
tab1, tab2, tab3 = st.tabs(["👨‍️ Pacientes", " Gráficas", " Alertas"])

# --- TAB 1: Lista de Pacientes ---
with tab1:
    st.header("Lista de Pacientes")
    
    if st.button("Consultar Pacientes"):
        try:
            response = requests.get(f"{BACKEND_URL}/fhir/Patient", headers=headers, timeout=30)
            
            if response.status_code == 200:
                pacientes = response.json()
                
                if pacientes:
                    df_pacientes = pd.DataFrame(pacientes)
                    st.dataframe(df_pacientes, use_container_width=True)
                    st.success(f"✅ {len(pacientes)} paciente(s) encontrado(s)")
                else:
                    st.info("No hay pacientes registrados")
            else:
                st.error(f"❌ Error {response.status_code}: {response.json()}")
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            st.warning("💡 El backend puede estar 'dormido'. Espera 30 segundos e intenta de nuevo.")

# --- TAB 2: Gráficas de Signos Vitales ---
with tab2:
    st.header("📈 Tendencias de Signos Vitales")
    
    if st.button("Cargar Observaciones"):
        try:
            response = requests.get(f"{BACKEND_URL}/fhir/Observation", headers=headers, timeout=30)
            
            if response.status_code == 200:
                observaciones = response.json()
                
                if observaciones:
                    df_obs = pd.DataFrame(observaciones)
                    
                    # Gráfica de líneas con Plotly
                    fig = px.line(df_obs, x="id", y="value", color="type", 
                                  title="Tendencias de Signos Vitales",
                                  labels={"value": "Valor", "type": "Tipo", "id": "ID Obs"})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar datos en tabla
                    st.dataframe(
                        df_obs[["patient_name", "type", "value", "unit"]].rename(
                            columns={"patient_name": "Paciente", "type": "Tipo", "value": "Valor", "unit": "Unidad"}
                        ),
                        use_container_width=True
                    )
                else:
                    st.info("No hay observaciones registradas")
            else:
                st.error(f"❌ Error {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")

# --- TAB 3: Alertas de Outliers (Guía E.3) ---
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