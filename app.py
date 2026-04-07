import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Regional V - Sistema Táctico",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SKIN: DARK TACTICAL MODE (CSS) ---
st.markdown("""
    <style>
    /* Fondo General Oscuro */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    
    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background-color: #1c212d;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-family: 'Courier New', Courier, monospace;
    }
    div[data-testid="stMetricLabel"] {
        color: #8b949e !important;
    }

    /* Botones Tácticos */
    .stButton>button {
        border-radius: 5px;
        font-weight: bold;
        text-transform: uppercase;
        border: 1px solid #30363d;
        transition: 0.3s;
    }
    
    /* Botón Guardar (Azul Brillante) */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #1f6feb;
        color: white;
        border: none;
    }
    
    /* Tablas estilo Dark */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 10px;
    }

    /* Sidebar Oscura */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Input Fields */
    input, select, textarea {
        background-color: #0d1117 !important;
        color: white !important;
        border: 1px solid #30363d !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES CON CACHÉ (EVITAR ERROR 429) ---
@st.cache_resource(ttl=600)
def conectar_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except:
        return None

@st.cache_data(ttl=60)
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

# --- SESIÓN ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

# --- LOGIN ---
if not st.session_state.logueado:
    _, col_log, _ = st.columns([1, 1, 1])
    with col_log:
        st.write("")
        st.title("📟 Terminal de Acceso")
        with st.form("login_form"):
            u = st.text_input("Credencial (DNI)")
            p = st.text_input("Código", type="password")
            if st.form_submit_button("AUTENTICAR"):
                sheet = conectar_gsheet()
                if sheet:
                    ws_u = sheet.worksheet("Usuarios")
                    df_u = pd.DataFrame(ws_u.get_all_records())
                    match = df_u[(df_u['Usuario'].astype(str) == u) & (df_u['Clave'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.logueado = True
                        st.rerun()
                    else:
                        st.error("Acceso denegado")
else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.subheader("OPERADOR CENTRAL")
        st.write("---")
        if st.button("SALIR DEL SISTEMA"):
            st.session_state.logueado = False
            st.session_state.lista_temporal = []
            st.rerun()

    st.title("👮‍♂️ Unidad Regional V - Sistema de Carga")
    
    df_nomina = obtener_datos_tabla("Nómina")
    df_reg = obtener_datos_tabla("Registros")

    # Métricas "Cyberpunk"
    m1, m2, m3 = st.columns(3)
    m1.metric("PENDIENTES", len(st.session_state.lista_temporal))
    m2.metric("EFECTIVOS", len(df_nomina))
    m3.metric("FECHA", datetime.now().strftime("%d/%m/%Y"))

    st.write("---")

    col_a, col_b = st.columns([1, 1.5], gap="large")

    with col_a:
        st.subheader("📥 Entrada de Datos")
        f_in = st.date_input("Fecha Servicio", datetime.now())
        f_str = f_in.strftime("%d/%m/%Y")
        
        nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
        agente = st.selectbox("Seleccionar Personal", ["---"] + nombres)
        detalle = st.text_input("Detalles / Observación")

        if agente != "---":
            datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
            dni = str(datos['DNI'])
            dep = datos['DEPENDENCIA']
            
            # Alerta de Duplicado Táctica
            if not df_reg.empty and 'DNI' in df_reg.columns:
                previos = df_reg[df_reg['DNI'].astype(str) == dni]
                if not previos.empty:
                    st.warning(f"⚠️ REGISTRO EXISTENTE PARA {agente}")
                    with st.expander("Ver Historial"):
                        st.dataframe(previos[['FECHA', 'DEPENDENCIA', 'OBSERVACIONES']], hide_index=True)

            if st.button("✚ AGREGAR A LA COLA"):
                st.session_state.lista_temporal.append({
                    "FECHA": f_str, "APELLIDO Y NOMBRES": agente,
                    "DNI": dni, "DEPENDENCIA": dep, "OBSERVACIONES": detalle
                })
                st.rerun()

    with col_b:
        st.subheader("📑 Cola de Impresión/Carga")
        if st.session_state.lista_temporal:
            df_temp = pd.DataFrame(st.session_state.lista_temporal)
            st.dataframe(df_temp, use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 TRANSMITIR DATOS A GOOGLE", type="primary"):
                    sheet = conectar_gsheet()
                    if sheet:
                        ws = sheet.worksheet("Registros")
                        for row in st.session_state.lista_temporal:
                            ws.append_row(list(row.values()))
                        st.balloons()
                        st.success("Transmisión Completada")
                        st.session_state.lista_temporal = []
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
            with c2:
                if st.button("🗑️ ABORTAR CARGA"):
                    st.session_state.lista_temporal = []
                    st.rerun()
        else:
            st.info("No hay datos en la cola de carga.")
