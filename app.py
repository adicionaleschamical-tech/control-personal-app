import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Servicios - Regional", layout="centered")

# Función de conexión robusta
def conectar_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- MANEJO DE SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
    st.session_state.user_data = {}

# --- FORMULARIO DE LOGIN ---
def login_screen():
    st.title("🔐 Acceso al Sistema")
    with st.form("login"):
        user_input = st.text_input("DNI Usuario")
        pass_input = st.text_input("Clave", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            sheet = conectar_gsheet()
            if sheet:
                # Leer pestaña Usuarios (Asegurate que se llame 'Usuarios' en el Sheet)
                df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                # Validar credenciales
                match = df_users[(df_users['DNI'].astype(str) == user_input) & 
                                 (df_users['CLAVE'].astype(str) == pass_input)]
                
                if not match.empty:
                    st.session_state.logueado = True
                    st.session_state.user_data = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Usuario o Clave incorrectos")

# --- APP PRINCIPAL ---
if not st.session_state.logueado:
    login_screen()
else:
    user = st.session_state.user_data
    st.sidebar.success(f"Sesión: {user['DNI']}")
    st.sidebar.info(f"Dependencia: {user['DEPENDENCIA']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.rerun()

    st.title("📝 Registro de Servicios")
    
    sheet = conectar_gsheet()
    if sheet:
        # 1. Cargar Nómina
        df_nomina = pd.DataFrame(sheet.worksheet("Nomina").get_all_records())
        
        # Filtro por Dependencia (Si es Admin ve todo, si no, solo lo suyo)
        if user['ROL'] == "Administrador":
            todas_deps = ["Todas"] + list(df_nomina['DEPENDENCIA'].unique())
            dep_seleccionada = st.selectbox("Filtrar Dependencia", todas_deps)
            if dep_seleccionada != "Todas":
                df_nomina = df_nomina[df_nomina['DEPENDENCIA'] == dep_seleccionada]
        else:
            df_nomina = df_nomina[df_nomina['DEPENDENCIA'] == user['DEPENDENCIA']]

        # 2. Formulario de Carga
        with st.form("registro_servicio"):
            fecha_sel = st.date_input("Fecha del Servicio", datetime.now())
            agente_sel = st.selectbox("Seleccionar Personal", df_nomina['APELLIDO Y NOMBRES'].tolist())
            observaciones = st.text_area("Observaciones (Opcional)")
            
            # Buscamos DNI del agente seleccionado
            dni_agente = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel]['DNI'].values[0]
            dep_agente = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel]['DEPENDENCIA'].values[0]
            
            # --- CHEQUEO DE DUPLICADOS EN PESTAÑA 'REGISTROS' ---
            df_registros = pd.DataFrame(sheet.worksheet("Registros").get_all_records())
            servicios_previos = df_registros[df_registros['DNI'].astype(str) == str(dni_agente)]
            
            ya_existe = not servicios_previos.empty
            autorizacion = True # Por defecto asumimos que puede
            
            if ya_existe:
                fechas = ", ".join(servicios_previos['FECHA'].astype(str).tolist())
                st.warning(f"⚠️ ATENCIÓN: {agente_sel} ya realizó servicios el: {fechas}")
                autorizacion = st.checkbox("Confirmar doble servicio (Doble Validación)")

            btn_registrar = st.form_submit_button("Registrar Servicio")

            if btn_registrar:
                if ya_existe and not autorizacion:
                    st.error("Debe marcar la casilla de confirmación para duplicar el servicio.")
                else:
                    nueva_fila = [str(fecha_sel), agente_sel, str(dni_agente), dep_agente, observaciones]
                    sheet.worksheet("Registros").append_row(nueva_fila)
                    st.success(f"✅ Servicio de {agente_sel} registrado con éxito.")
