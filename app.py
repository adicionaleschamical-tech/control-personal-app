import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Regional V - Sistema Táctico",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURACIÓN DE ENTORNO ---
ENV = os.getenv("STREAMLIT_ENV", "production")
DEBUG = ENV == "development"

# --- SKIN: DARK TACTICAL MODE (COMPLETAMENTE OSCURO) ---
st.markdown("""
    <style>
    /* Fondo General Oscuro - Forzar todo */
    .stApp, .stApp > header, .stApp > footer, .main > div {
        background-color: #0a0c10 !important;
    }
    
    /* Forzar fondo de todos los contenedores */
    div[data-testid="stVerticalBlock"], 
    div[data-testid="stHorizontalBlock"],
    div[data-testid="column"],
    div[data-testid="stForm"],
    div[class*="css-"] {
        background-color: transparent !important;
    }
    
    /* Texto general */
    html, body, [class*="css"] {
        color: #ffffff !important;
    }
    
    p, div, span, label, .stMarkdown, .stText {
        color: #e6edf3 !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background-color: #1a1f2e !important;
        border: 1px solid #2d3348;
        border-radius: 12px;
        padding: 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-size: 2rem !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #c9d1d9 !important;
    }
    
    /* Botones */
    .stButton>button {
        border-radius: 6px;
        font-weight: bold;
        text-transform: uppercase;
        border: 1px solid #2d3348;
        color: #ffffff !important;
        background-color: #21262d !important;
    }
    .stButton>button:hover {
        border-color: #58a6ff;
        background-color: #2d3348 !important;
    }
    
    /* Botón Guardar */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #1f6feb !important;
        color: white !important;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #388bfd !important;
    }
    
    /* Tablas */
    .stDataFrame {
        border: 1px solid #2d3348;
        border-radius: 10px;
        background-color: #0d1117 !important;
    }
    .dataframe {
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
    }
    .dataframe th {
        background-color: #1a1f2e !important;
        color: #58a6ff !important;
        padding: 10px !important;
    }
    .dataframe td {
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
        padding: 8px !important;
    }
    .dataframe tr:hover td {
        background-color: #1a1f2e !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0d1117 !important;
        border-right: 1px solid #2d3348;
    }
    section[data-testid="stSidebar"] * {
        color: #e6edf3 !important;
    }
    
    /* Input Fields */
    input, select {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
        border: 1px solid #2d3348 !important;
        border-radius: 6px !important;
    }
    input:focus, select:focus {
        border-color: #58a6ff !important;
    }
    
    /* Labels */
    .stTextInput label, .stSelectbox label, .stDateInput label {
        color: #c9d1d9 !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1a1f2e !important;
        color: #58a6ff !important;
        border: 1px solid #2d3348;
    }
    .streamlit-expanderContent {
        background-color: #0d1117 !important;
        border: 1px solid #2d3348;
    }
    
    /* Alertas */
    .stAlert {
        background-color: #1a1f2e !important;
        color: #e6edf3 !important;
    }
    .stSuccess {
        background-color: #1a3a2a !important;
    }
    .stError {
        background-color: #3a1a1a !important;
    }
    .stWarning {
        background-color: #3a2a1a !important;
    }
    .stInfo {
        background-color: #1a2a3a !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1f2e !important;
        color: #c9d1d9 !important;
        border: 1px solid #2d3348;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
    }
    
    /* Formularios */
    .stForm {
        background-color: transparent !important;
    }
    
    /* Dividers */
    hr {
        border-color: #2d3348 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES ---
def notificar(mensaje, tipo="info"):
    if tipo == "success":
        st.toast(f"✅ {mensaje}", icon="🎉")
    elif tipo == "error":
        st.toast(f"❌ {mensaje}", icon="⚠️")
    elif tipo == "warning":
        st.toast(f"⚠️ {mensaje}", icon="📢")
    else:
        st.toast(f"ℹ️ {mensaje}", icon="📋")

def log_accion(usuario, accion, detalles):
    try:
        sheet = conectar_gsheet()
        if sheet:
            try:
                ws_log = sheet.worksheet("Logs")
                ws_log.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(usuario),
                    accion,
                    str(detalles)
                ])
            except:
                try:
                    ws_log = sheet.add_worksheet(title="Logs", rows="1000", cols="20")
                    ws_log.append_row(["TIMESTAMP", "USUARIO", "ACCION", "DETALLES"])
                except:
                    pass
    except:
        pass

@st.cache_resource(ttl=600)
def conectar_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except Exception as e:
        if DEBUG:
            st.error(f"Error: {str(e)}")
        return None

@st.cache_data(ttl=60)
def obtener_datos_tabla(nombre_pestaña):
    try:
        sheet = conectar_gsheet()
        if not sheet:
            return pd.DataFrame()
        
        ws = sheet.worksheet(nombre_pestaña)
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def cargar_nomina():
    return obtener_datos_tabla("Nómina")

def guardar_registro(datos):
    try:
        sheet = conectar_gsheet()
        if not sheet:
            return False, "Sin conexión"
        
        ws = sheet.worksheet("Registros")
        ws.append_row(list(datos.values()))
        return True, "Registro guardado"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

# --- INICIALIZACIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- LOGIN ---
if not st.session_state.logueado:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.title("📟 Terminal de Acceso")
        st.markdown("---")
        with st.form("login_form"):
            u = st.text_input("DNI", placeholder="Ingrese su DNI")
            p = st.text_input("Clave", type="password", placeholder="Contraseña")
            submitted = st.form_submit_button("🔐 AUTENTICAR", use_container_width=True)
            
            if submitted:
                if not u or not p:
                    st.error("Complete todos los campos")
                else:
                    sheet = conectar_gsheet()
                    if sheet:
                        try:
                            ws_u = sheet.worksheet("Usuarios")
                            df_u = pd.DataFrame(ws_u.get_all_records())
                            match = df_u[(df_u['Usuario'].astype(str) == u) & (df_u['Clave'].astype(str) == p)]
                            if not match.empty:
                                st.session_state.logueado = True
                                st.session_state.user_info = {
                                    'dni': u,
                                    'nombre': match.iloc[0].get('NOMBRE', u),
                                    'rol': match.iloc[0].get('ROL', 'OPERADOR')
                                }
                                log_accion(u, "LOGIN", "Exitoso")
                                notificar(f"Bienvenido", "success")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Acceso denegado")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                    else:
                        st.error("Error de conexión")
else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=80)
        st.markdown(f"### {st.session_state.user_info.get('nombre', 'OPERADOR')}")
        st.caption(f"{st.session_state.user_info.get('rol', 'OPERADOR')}")
        st.write("---")
        
        if st.button("SALIR", use_container_width=True):
            log_accion(st.session_state.user_info.get('dni', ''), "LOGOUT", "Cierre")
            st.session_state.logueado = False
            st.session_state.user_info = {}
            st.rerun()
        
        st.caption(f"Versión: 3.0")
        st.caption(f"{datetime.now().strftime('%d/%m/%Y %H:%M')}")

    st.title("👮‍♂️ Unidad Regional V")
    
    # Cargar datos
    with st.spinner("Cargando..."):
        df_nomina = cargar_nomina()
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("EFECTIVOS", len(df_nomina))
    c2.metric("FECHA", datetime.now().strftime("%d/%m/%Y"))
    c3.metric("OPERADOR", st.session_state.user_info.get('nombre', '---')[:20])
    
    st.write("---")
    
    # Formulario principal
    col_form, col_info = st.columns([1.2, 1])
    
    with col_form:
        st.subheader("REGISTRO DE SERVICIO")
        
        with st.form("registro", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.now())
            fecha_str = fecha.strftime("%d/%m/%Y")
            
            # Buscador
            busqueda = st.text_input("Buscar", placeholder="Nombre o DNI...")
            
            nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            if busqueda:
                nombres = [n for n in nombres if busqueda.lower() in n.lower()]
            
            if not nombres:
                st.warning("No se encontraron efectivos")
                agente = None
            else:
                agente = st.selectbox("Personal", ["---"] + nombres)
            
            enviar = st.form_submit_button("GUARDAR", type="primary", use_container_width=True)
            
            if enviar and agente and agente != "---":
                datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                dni = str(datos['DNI'])
                dep = datos['DEPENDENCIA']
                
                registro = {
                    "FECHA": fecha_str,
                    "APELLIDO Y NOMBRES": agente,
                    "DNI": dni,
                    "DEPENDENCIA": dep
                }
                
                with st.spinner("Guardando..."):
                    ok, msg = guardar_registro(registro)
                    if ok:
                        st.balloons()
                        notificar(msg, "success")
                        log_accion(st.session_state.user_info.get('dni', ''), "REGISTRO", f"{agente} - {fecha_str}")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
            elif enviar and (not agente or agente == "---"):
                st.warning("Seleccione un efectivo")
    
    with col_info:
        st.subheader("ÚLTIMOS REGISTROS")
        
        df_reg = obtener_datos_tabla("Registros")
        
        if not df_reg.empty:
            # Mostrar últimos registros sin observaciones
            df_recent = df_reg.head(10)[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']]
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros")
    
    # Estadísticas
    st.write("---")
    with st.expander("DISTRIBUCIÓN POR DEPENDENCIA"):
        if not df_nomina.empty:
            dep_count = df_nomina['DEPENDENCIA'].value_counts()
            cols = st.columns(3)
            for i, (dep, cnt) in enumerate(dep_count.items()):
                with cols[i % 3]:
                    st.metric(dep, cnt)

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #8b949e;'>Regional V - Sistema de Gestión</p>", 
    unsafe_allow_html=True
)
