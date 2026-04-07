import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sistema Regional de Servicios",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO VISUAL (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #003366; font-weight: 700; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button { border-radius: 8px; height: 3em; font-weight: bold; }
    div.stButton > button:first-child[kind="primary"] { background-color: #003366; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES CON CACHÉ PARA EVITAR ERROR 429 ---

@st.cache_resource(ttl=600)
def conectar_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except Exception as e:
        return None

@st.cache_data(ttl=60) # Actualiza los datos automáticamente cada 1 minuto
def obtener_datos_tabla(nombre_pestaña):
    sheet = conectar_gsheet()
    if sheet:
        try:
            ws = sheet.worksheet(nombre_pestaña)
            data = ws.get_all_values()
            if len(data) > 0:
                df = pd.DataFrame(data[1:], columns=data[0])
                df.columns = [c.strip() for c in df.columns]
                return df
            return pd.DataFrame()
        except:
            return pd.DataFrame()
    return None

# --- MANEJO DE SESIÓN ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.title("🔐 Acceso")
        with st.form("login_form"):
            u = st.text_input("Usuario (DNI)")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("INGRESAR"):
                # Para el login no usamos caché para asegurar que sea en tiempo real
                sheet = conectar_gsheet()
                if sheet:
                    ws_user = sheet.worksheet("Usuarios")
                    df_users = pd.DataFrame(ws_user.get_all_records())
                    match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.logueado = True
                        st.rerun()
                    else:
                        st.error("Datos incorrectos")
else:
    # --- INTERFAZ PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=80)
        st.title("UR-V Región")
        if st.button("CERRAR SESIÓN"):
            st.session_state.logueado = False
            st.session_state.lista_temporal = []
            st.rerun()

    st.title("👮‍♂️ Carga de Servicios Regionales")
    
    # Obtener datos usando la función con caché
    df_nomina = obtener_datos_tabla("Nómina")
    df_reg = obtener_datos_tabla("Registros")

    if df_nomina is not None:
        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("📦 En espera", len(st.session_state.lista_temporal))
        m2.metric("👥 Nómina", len(df_nomina))
        m3.metric("📅 Fecha", datetime.now().strftime("%d/%m/%Y"))

        st.divider()

        col_c, col_v = st.columns([1, 1.4], gap="large")

        with col_c:
            st.subheader("📝 Nuevo Registro")
            fecha_input = st.date_input("Fecha", datetime.now())
            fecha_str = fecha_input.strftime("%d/%m/%Y")
            
            lista_personal = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
            agente = st.selectbox("Efectivo", ["--- Seleccione ---"] + lista_personal)
            obs = st.text_input("Observaciones")

            if agente != "--- Seleccione ---":
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                dni_ag = str(datos_ag['DNI'])
                dep_ag = datos_ag['DEPENDENCIA']
                
                # Validación de duplicados
                if not df_reg.empty and 'DNI' in df_reg.columns:
                    previos = df_reg[df_reg['DNI'].astype(str) == dni_ag]
                    if not previos.empty:
                        st.warning(f"⚠️ {agente} ya tiene registros previos.")
                        with st.expander("Ver historial"):
                            st.dataframe(previos[['FECHA', 'DEPENDENCIA', 'OBSERVACIONES']], hide_index=True)

                if st.button("➕ AÑADIR A LA LISTA"):
                    st.session_state.lista_temporal.append({
                        "FECHA": fecha_str,
                        "APELLIDO Y NOMBRES": agente,
                        "DNI": dni_ag,
                        "DEPENDENCIA": dep_ag,
                        "OBSERVACIONES": obs
                    })
                    st.rerun()

        with col_v:
            st.subheader("📋 Revisión")
            if st.session_state.lista_temporal:
                df_temp = pd.DataFrame(st.session_state.lista_temporal)
                st.dataframe(df_temp[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA', 'OBSERVACIONES']], 
                             use_container_width=True, hide_index=True)
                
                c_env, c_vac = st.columns(2)
                with c_env:
                    if st.button("🚀 GUARDAR TODO", type="primary"):
                        sheet = conectar_gsheet()
                        if sheet:
                            ws_reg = sheet.worksheet("Registros")
                            for item in st.session_state.lista_temporal:
                                ws_reg.append_row(list(item.values()))
                            st.balloons()
                            st.success("Guardado con éxito")
                            st.session_state.lista_temporal = []
                            # Limpiamos caché para que el historial se actualice
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                with c_vac:
                    if st.button("🗑️ VACIAR"):
                        st.session_state.lista_temporal = []
                        st.rerun()
            else:
                st.info("Lista vacía")
