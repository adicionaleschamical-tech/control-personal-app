import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carga Rápida de Servicios", layout="wide")

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

# --- MANEJO DE SESIÓN PARA LA LISTA TEMPORAL ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

# --- LOGIN ---
if not st.session_state.logueado:
    st.title("🔐 Acceso Sistema de Carga")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            sheet = conectar_gsheet()
            if sheet:
                df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                df_users.columns = [c.strip() for c in df_users.columns]
                match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                if not match.empty:
                    st.session_state.logueado = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
else:
    # --- INTERFAZ DE CARGA DIRECTA ---
    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"logueado": False, "lista_temporal": []}))
    
    st.title("📝 Registro de Servicios Regional")
    
    sheet = conectar_gsheet()
    if sheet:
        # 1. Cargar Datos (Nómina completa y Registros históricos)
        df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
        df_nomina.columns = [c.strip() for c in df_nomina.columns]
        
        data_reg = sheet.worksheet("Registros").get_all_records()
        df_reg = pd.DataFrame(data_reg) if data_reg else pd.DataFrame(columns=['FECHA', 'APELLIDO Y NOMBRES', 'DNI', 'DEPENDENCIA', 'OBSERVACIONES'])
        if not df_reg.empty: 
            df_reg.columns = [c.strip() for c in df_reg.columns]

        # --- DISEÑO DE COLUMNAS ---
        col_input, col_lista = st.columns([1, 1.2])
        
        with col_input:
            st.subheader("Entrada de Datos")
            
            # 1. Fecha (Sistema por defecto)
            fecha_sel = st.date_input("Fecha del Servicio", datetime.now())
            
            # 2. Selector de Personal (Búsqueda global)
            nombres_completos = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
            agente_sel = st.selectbox("Buscar Efectivo", ["--- Seleccione un nombre ---"] + nombres_completos)
            
            # 3. Observaciones
            obs = st.text_input("Observaciones")

            # --- VALIDACIÓN DE DUPLICADOS EN TIEMPO REAL ---
            if agente_sel != "--- Seleccione un nombre ---":
                # Extraer datos técnicos del agente
                datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel].iloc[0]
                dni_actual = str(datos['DNI'])
                dep_actual = datos['DEPENDENCIA']
                
                # Buscar en el historial de 'Registros'
                servicios_previos = df_reg[df_reg['DNI'].astype(str) == dni_actual]
                
                if not servicios_previos.empty:
                    # Mostrar alerta con las fechas donde ya trabajó
                    fechas_ocupadas = ", ".join(servicios_previos['FECHA'].astype(str).unique().tolist())
                    st.warning(f"⚠️ **AVISO:** {agente_sel} ya tiene servicios registrados el: {fechas_ocupadas}")
                
                if st.button("➕ Añadir a la lista"):
                    st.session_state.lista_temporal.append({
                        "FECHA": str(fecha_sel),
                        "APELLIDO Y NOMBRES": agente_sel,
                        "DNI": dni_actual,
                        "DEPENDENCIA": dep_actual,
                        "OBSERVACIONES": obs
                    })
                    st.rerun()

        with col_lista:
            st.subheader("Lista para enviar al Sheet")
            if st.session_state.lista_temporal:
                df_temp = pd.DataFrame(st.session_state.lista_temporal)
                st.dataframe(df_temp[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']], use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🚀 CONFIRMAR Y GUARDAR TODO"):
                        with st.spinner("Registrando..."):
                            pestaña_reg = sheet.worksheet("Registros")
                            for row in st.session_state.lista_temporal:
                                pestaña_reg.append_row(list(row.values()))
                            st.success(f"Se guardaron {len(st.session_state.lista_temporal)} registros.")
                            st.session_state.lista_temporal = []
                            st.rerun()
                with c2:
                    if st.button("🗑️ Borrar lista"):
                        st.session_state.lista_temporal = []
                        st.rerun()
            else:
                st.info("La lista está vacía.")
