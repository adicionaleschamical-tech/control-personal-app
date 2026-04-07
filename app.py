import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Servicios - Regional", layout="wide")

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
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []

# --- LOGIN ---
if not st.session_state.logueado:
    st.title("🔐 Acceso al Sistema")
    with st.form("login"):
        u = st.text_input("Usuario (DNI)")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            sheet = conectar_gsheet()
            if sheet:
                df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                df_users.columns = [c.strip() for c in df_users.columns]
                match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                if not match.empty:
                    st.session_state.logueado = True
                    st.session_state.user_data = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
else:
    # --- INTERFAZ PRINCIPAL ---
    user = st.session_state.user_data
    # Normalizar nombres de columnas de la sesión
    dep_usuario = user.get('Dependencia') or user.get('DEPENDENCIA')
    
    st.sidebar.success(f"Usuario: {user['Usuario']}")
    st.sidebar.info(f"Dependencia: {dep_usuario}")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.session_state.lista_temporal = []
        st.rerun()

    st.title(f"📝 Carga de Servicios - {dep_usuario}")
    
    sheet = conectar_gsheet()
    if sheet:
        # Cargar Datos de Nómina y Registros
        df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
        df_nomina.columns = [c.strip() for c in df_nomina.columns]
        
        data_reg = sheet.worksheet("Registros").get_all_records()
        df_reg = pd.DataFrame(data_reg) if data_reg else pd.DataFrame(columns=['FECHA', 'APELLIDO Y NOMBRES', 'DNI', 'DEPENDENCIA', 'OBSERVACIONES'])
        if not df_reg.empty: 
            df_reg.columns = [c.strip() for c in df_reg.columns]

        # --- FILTRADO AUTOMÁTICO POR DEPENDENCIA ---
        # El sistema ya sabe qué dependencia cargar basándose en el usuario logueado
        df_filtro = df_nomina[df_nomina['DEPENDENCIA'] == dep_usuario]

        if df_filtro.empty:
            st.warning(f"No se encontró personal cargado para la dependencia: {dep_usuario}")
        else:
            # --- ÁREA DE CARGA ---
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Selección de Personal")
                
                # Fecha editable (hoy por defecto)
                fecha_servicio = st.date_input("Fecha del Servicio", datetime.now())
                
                agente = st.selectbox("Seleccionar Efectivo", df_filtro['APELLIDO Y NOMBRES'].tolist())
                obs_adicional = st.text_input("Observaciones (opcional)")
                
                # Obtener DNI para validación
                dni_agente = str(df_filtro[df_filtro['APELLIDO Y NOMBRES'] == agente]['DNI'].values[0])
                
                # Advertencia si ya tiene registros previos en la base de datos
                if 'DNI' in df_reg.columns:
                    previos = df_reg[df_reg['DNI'].astype(str) == dni_agente]
                    if not previos.empty:
                        fechas_viejas = ", ".join(previos['FECHA'].astype(str).unique().tolist())
                        st.warning(f"⚠️ {agente} ya registra servicios anteriores (Fechas: {fechas_viejas})")

                if st.button("➕ Añadir a la Lista"):
                    nuevo_registro = {
                        "FECHA": str(fecha_servicio),
                        "APELLIDO Y NOMBRES": agente,
                        "DNI": dni_agente,
                        "DEPENDENCIA": dep_usuario,
                        "OBSERVACIONES": obs_adicional
                    }
                    st.session_state.lista_temporal.append(nuevo_registro)
                    st.rerun()

            with col2:
                st.subheader("Registros en espera")
                if st.session_state.lista_temporal:
                    df_vista = pd.DataFrame(st.session_state.lista_temporal)
                    st.dataframe(df_vista[['FECHA', 'APELLIDO Y NOMBRES']], use_container_width=True)
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("🚀 ENVIAR TODO AL SHEET"):
                            with st.spinner("Guardando..."):
                                pestaña_reg = sheet.worksheet("Registros")
                                for item in st.session_state.lista_temporal:
                                    pestaña_reg.append_row(list(item.values()))
                                st.success("¡Registros guardados!")
                                st.session_state.lista_temporal = []
                                st.rerun()
                    with col_b2:
                        if st.button("🗑️ Vaciar Lista"):
                            st.session_state.lista_temporal = []
                            st.rerun()
                else:
                    st.info("La lista está vacía. Seleccione personal a la izquierda.")
