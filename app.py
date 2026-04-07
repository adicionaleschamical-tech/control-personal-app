import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Servicios - Regional", layout="centered")

# Función de conexión
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
        user_input = st.text_input("Usuario (DNI)")
        pass_input = st.text_input("Clave", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            sheet = conectar_gsheet()
            if sheet:
                # Leer pestaña Usuarios
                df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                
                # Ajustamos la búsqueda a tus nombres: 'Usuario' y 'Clave'
                match = df_users[(df_users['Usuario'].astype(str) == user_input) & 
                                 (df_users['Clave'].astype(str) == pass_input)]
                
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
    st.sidebar.success(f"Sesión: {user['Usuario']}")
    st.sidebar.info(f"Dependencia: {user['Dependencia']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.rerun()

    st.title("📝 Registro de Servicios")
    
    sheet = conectar_gsheet()
    if sheet:
        # 1. Cargar Nómina (con tilde como me pasaste)
        df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
        
        # Filtro por Dependencia (Admin ve todo, Usuario solo lo suyo)
        if user['Rol'] == "Administrador":
            todas_deps = ["Todas"] + list(df_nomina['DEPENDENCIA'].unique())
            dep_seleccionada = st.selectbox("Filtrar Dependencia", todas_deps)
            if dep_seleccionada != "Todas":
                df_nomina = df_nomina[df_nomina['DEPENDENCIA'] == dep_seleccionada]
        else:
            df_nomina = df_nomina[df_nomina['DEPENDENCIA'] == user['Dependencia']]

        # 2. Formulario de Carga
        if not df_nomina.empty:
            with st.form("registro_servicio"):
                fecha_sel = st.date_input("Fecha del Servicio", datetime.now())
                agente_sel = st.selectbox("Seleccionar Personal", df_nomina['APELLIDO Y NOMBRES'].tolist())
                observaciones = st.text_area("OBSERVACIONES")
                
                # Extraer datos del agente seleccionado
                datos_agente = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel].iloc[0]
                dni_agente = datos_agente['DNI']
                dep_agente = datos_agente['DEPENDENCIA']
                
                # --- DOBLE VALIDACIÓN EN 'REGISTROS' ---
                df_registros = pd.DataFrame(sheet.worksheet("Registros").get_all_records())
                # Buscamos si ya existe ese DNI en Registros
                ya_existe = not df_registros[df_registros['DNI'].astype(str) == str(dni_agente)].empty
                
                autorizacion = True
                if ya_existe:
                    servicios_viejos = df_registros[df_registros['DNI'].astype(str) == str(dni_agente)]
                    fechas = ", ".join(servicios_viejos['FECHA'].astype(str).tolist())
                    st.warning(f"⚠️ {agente_sel} ya tiene servicios registrados el: {fechas}")
                    autorizacion = st.checkbox("Confirmar Doble Servicio (Doble Validación)")

                btn_registrar = st.form_submit_button("Registrar en Sheet")

                if btn_registrar:
                    if ya_existe and not autorizacion:
                        st.error("Debe marcar la casilla de confirmación para duplicar el servicio.")
                    else:
                        # Respetamos el orden de tus columnas: FECHA, APELLIDO Y NOMBRES, DNI, DEPENDENCIA, OBSERVACIONES
                        nueva_fila = [str(fecha_sel), agente_sel, str(dni_agente), dep_agente, observaciones]
                        sheet.worksheet("Registros").append_row(nueva_fila)
                        st.success(f"✅ Servicio de {agente_sel} registrado con éxito.")
        else:
            st.warning("No hay personal cargado para esta dependencia.")
