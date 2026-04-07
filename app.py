import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
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

# --- SESIÓN ---
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
                # Limpiamos nombres de columnas de Usuarios
                df_users.columns = [c.strip() for c in df_users.columns]
                match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                if not match.empty:
                    st.session_state.logueado = True
                    st.session_state.user_data = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
else:
    # --- APP PRINCIPAL ---
    user = st.session_state.user_data
    st.sidebar.success(f"Usuario: {user['Usuario']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.session_state.lista_temporal = []
        st.rerun()

    st.title("📝 Carga Masiva de Servicios")
    
    sheet = conectar_gsheet()
    if sheet:
        # Cargar Nómina
        df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
        df_nomina.columns = [c.strip() for c in df_nomina.columns]

        # Cargar Registros con validación
        data_reg = sheet.worksheet("Registros").get_all_records()
        if not data_reg:
            # Si está vacío, creamos un DataFrame con las columnas correctas
            df_reg = pd.DataFrame(columns=['FECHA', 'APELLIDO Y NOMBRES', 'DNI', 'DEPENDENCIA', 'OBSERVACIONES'])
        else:
            df_reg = pd.DataFrame(data_reg)
            df_reg.columns = [c.strip() for c in df_reg.columns]

        # Filtro de dependencia
        rol_key = 'Rol' if 'Rol' in user else 'ROL'
        dep_key = 'Dependencia' if 'Dependencia' in user else 'DEPENDENCIA'
        
        if user[rol_key] == "Administrador":
            dep_sel = st.selectbox("Dependencia", ["Todas"] + list(df_nomina['DEPENDENCIA'].unique()))
            df_filtro = df_nomina if dep_sel == "Todas" else df_nomina[df_nomina['DEPENDENCIA'] == dep_sel]
        else:
            df_filtro = df_nomina[df_nomina['DEPENDENCIA'] == user[dep_key]]

        # --- SECCIÓN 1: AGREGAR A LA LISTA ---
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Añadir Efectivo")
            fecha = st.date_input("Fecha", datetime.now())
            lista_personal = df_filtro['APELLIDO Y NOMBRES'].tolist()
            agente = st.selectbox("Efectivo", lista_personal)
            obs = st.text_input("Observaciones")
            
            # Validación de existencia de columna DNI en Registros antes de buscar
            if 'DNI' in df_reg.columns:
                dni_agente = df_filtro[df_filtro['APELLIDO Y NOMBRES'] == agente]['DNI'].values[0]
                ya_registrado = df_reg[df_reg['DNI'].astype(str) == str(dni_agente)]
                
                if not ya_registrado.empty:
                    fechas_previas = ", ".join(ya_registrado['FECHA'].astype(str).tolist())
                    st.warning(f"⚠️ {agente} ya tiene servicios el: {fechas_previas}")
            
            if st.button("➕ Agregar a la lista"):
                datos_agente = df_filtro[df_filtro['APELLIDO Y NOMBRES'] == agente].iloc[0]
                nuevo_item = {
                    "FECHA": str(fecha),
                    "APELLIDO Y NOMBRES": agente,
                    "DNI": str(dni_agente),
                    "DEPENDENCIA": datos_agente['DEPENDENCIA'],
                    "OBSERVACIONES": obs
                }
                st.session_state.lista_temporal.append(nuevo_item)
                st.rerun()

        # --- SECCIÓN 2: VISTA PREVIA Y CONFIRMACIÓN ---
        with col2:
            st.subheader("Lista para enviar")
            if st.session_state.lista_temporal:
                df_temp = pd.DataFrame(st.session_state.lista_temporal)
                st.table(df_temp[['APELLIDO Y NOMBRES', 'DNI']])
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ Limpiar Lista"):
                        st.session_state.lista_temporal = []
                        st.rerun()
                with col_btn2:
                    if st.button("🚀 CONFIRMAR Y REGISTRAR TODO"):
                        with st.spinner("Registrando..."):
                            pestaña_reg = sheet.worksheet("Registros")
                            # Convertimos cada diccionario a lista respetando el orden del Sheet
                            for item in st.session_state.lista_temporal:
                                fila = [item["FECHA"], item["APELLIDO Y NOMBRES"], item["DNI"], item["DEPENDENCIA"], item["OBSERVACIONES"]]
                                pestaña_reg.append_row(fila)
                            
                            st.success(f"Se registraron {len(st.session_state.lista_temporal)} servicios.")
                            st.session_state.lista_temporal = []
                            st.rerun()
            else:
                st.info("La lista está vacía.")
