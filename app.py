import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (ESTILO MODERNO) ---
st.set_page_config(
    page_title="Gestión de Servicios Regional",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado para mejorar la estética
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #1f77b4;
    }
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        border-color: #1f77b4;
        color: #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    col_login, _ = st.columns([1, 2])
    with col_login:
        st.title("🔐 Acceso al Sistema")
        st.write("Control Centralizado de Servicios")
        with st.form("login_form"):
            u = st.text_input("Usuario", placeholder="DNI")
            p = st.text_input("Clave", type="password", placeholder="••••••••")
            if st.form_submit_button("Iniciar Sesión"):
                sheet = conectar_gsheet()
                if sheet:
                    df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                    df_users.columns = [c.strip() for c in df_users.columns]
                    match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.logueado = True
                        st.rerun()
                    else:
                        st.error("Usuario o clave incorrectos")
else:
    # --- INTERFAZ PRINCIPAL ---
    with st.sidebar:
        st.header("👮‍♂️ Menú")
        st.write(f"Estado: **En línea**")
        st.write("---")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"logueado": False, "lista_temporal": []})
            st.rerun()

    st.title("👮‍♂️ Registro de Servicios Regional")
    
    sheet = conectar_gsheet()
    if sheet:
        # Carga de datos con limpieza de columnas
        with st.spinner("Sincronizando datos..."):
            df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
            df_nomina.columns = [c.strip() for c in df_nomina.columns]
            
            data_reg = sheet.worksheet("Registros").get_all_records()
            df_reg = pd.DataFrame(data_reg) if data_reg else pd.DataFrame(columns=['FECHA', 'APELLIDO Y NOMBRES', 'DNI', 'DEPENDENCIA', 'OBSERVACIONES'])
            if not df_reg.empty: df_reg.columns = [c.strip() for c in df_reg.columns]

        # Métricas de la cabecera
        m1, m2, m3 = st.columns(3)
        m1.metric("Efectivos en lista", len(st.session_state.lista_temporal))
        m2.metric("Nómina Total", len(df_nomina))
        m3.metric("Fecha Sistema", datetime.now().strftime("%d/%m/%Y"))

        st.divider()

        col_input, col_preview = st.columns([1, 1.5], gap="large")

        with col_input:
            st.subheader("➕ Carga de Efectivo")
            
            # Fecha: Hoy por defecto, editable
            fecha_sel = st.date_input("Fecha del Servicio", datetime.now())
            
            # Lista desplegable con búsqueda rápida
            nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
            agente_sel = st.selectbox("Seleccionar Efectivo", ["--- Escriba el nombre ---"] + nombres)
            
            obs = st.text_input("Observaciones", placeholder="Opcional...")

            if agente_sel != "--- Escriba el nombre ---":
                # Extraer datos automáticos
                datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel].iloc[0]
                dni = str(datos['DNI'])
                dep = datos['DEPENDENCIA']
                
                # VALIDACIÓN DE DUPLICADOS
                if 'DNI' in df_reg.columns:
                    previos = df_reg[df_reg['DNI'].astype(str) == dni]
                    if not previos.empty:
                        fechas_viejas = ", ".join(previos['FECHA'].astype(str).unique().tolist())
                        st.warning(f"⚠️ **ATENCIÓN:** {agente_sel} ya tiene registros el día: {fechas_viejas}")
                        with st.expander("Ver detalles del historial"):
                            st.table(previos[['FECHA', 'DEPENDENCIA', 'OBSERVACIONES']])

                if st.button("➕ Añadir a la Lista", type="secondary"):
                    st.session_state.lista_temporal.append({
                        "FECHA": str(fecha_sel),
                        "APELLIDO Y NOMBRES": agente_sel,
                        "DNI": dni,
                        "DEPENDENCIA": dep,
                        "OBSERVACIONES": obs
                    })
                    st.rerun()

        with col_preview:
            st.subheader("📝 Revisión de Registros")
            if st.session_state.lista_temporal:
                df_temp = pd.DataFrame(st.session_state.lista_temporal)
                st.dataframe(df_temp[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA', 'OBSERVACIONES']], 
                             use_container_width=True, hide_index=True)
                
                st.write("")
                c_env, c_vac = st.columns(2)
                with c_env:
                    if st.button("🚀 GUARDAR TODO EN EL SHEET", type="primary"):
                        with st.spinner("Registrando en Google Sheets..."):
                            pestaña_reg = sheet.worksheet("Registros")
                            # Inyectar filas una por una
                            for row in st.session_state.lista_temporal:
                                pestaña_reg.append_row(list(row.values()))
                            
                            st.balloons()
                            st.success(f"¡Se guardaron {len(st.session_state.lista_temporal)} servicios correctamente!")
                            st.session_state.lista_temporal = []
                            # st.rerun() se omite para que el usuario vea el mensaje de éxito
                with c_vac:
                    if st.button("🗑️ Vaciar Lista Actual"):
                        st.session_state.lista_temporal = []
                        st.rerun()
            else:
                st.info("La lista está vacía. Comience seleccionando personal a la izquierda.")
