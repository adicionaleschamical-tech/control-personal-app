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

# --- SKIN: DARK TACTICAL MODE (TODOS LOS FONDOS OSCUROS) ---
st.markdown("""
    <style>
    /* Fondo General Oscuro */
    .stApp {
        background-color: #0a0c10;
        color: #ffffff;
    }
    
    /* Resetear todos los fondos blancos */
    .stApp > header,
    .stApp > footer,
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        background-color: #0a0c10 !important;
    }
    
    /* Texto general */
    body, p, div, span, label, .stMarkdown {
        color: #e6edf3 !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* Tarjetas de Métricas - Fondo oscuro */
    div[data-testid="stMetric"] {
        background-color: #1a1f2e !important;
        border: 1px solid #2d3348;
        border-radius: 12px;
        padding: 20px;
    }
    div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-family: 'Courier New', Courier, monospace;
        font-size: 2rem !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #c9d1d9 !important;
        font-weight: 500 !important;
    }
    
    /* Botones */
    .stButton>button {
        border-radius: 6px;
        font-weight: bold;
        text-transform: uppercase;
        border: 1px solid #2d3348;
        transition: all 0.3s ease;
        width: 100%;
        color: #ffffff !important;
        background-color: #21262d !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        border-color: #58a6ff;
        color: #ffffff !important;
        background-color: #2d3348 !important;
    }
    
    /* Botón Guardar */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #1f6feb !important;
        color: white !important;
        border: none;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #388bfd !important;
    }
    
    /* Tablas - Todo oscuro */
    .stDataFrame {
        border: 1px solid #2d3348;
        border-radius: 10px;
        background-color: #0d1117 !important;
    }
    .dataframe {
        font-size: 14px;
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
    }
    .dataframe th {
        background-color: #1a1f2e !important;
        color: #58a6ff !important;
        font-weight: bold !important;
        padding: 10px !important;
        border-bottom: 1px solid #2d3348 !important;
    }
    .dataframe td {
        color: #e6edf3 !important;
        background-color: #0d1117 !important;
        padding: 8px !important;
        border-bottom: 1px solid #1a1f2e !important;
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
    input, select, textarea {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
        border: 1px solid #2d3348 !important;
        border-radius: 6px !important;
    }
    input:focus, select:focus, textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
    }
    input::placeholder, textarea::placeholder {
        color: #8b949e !important;
    }
    
    /* Labels */
    .stTextInput label, .stSelectbox label, .stDateInput label, .stTextArea label {
        color: #c9d1d9 !important;
        font-weight: 500 !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1a1f2e !important;
        border-radius: 6px;
        color: #58a6ff !important;
        font-weight: 500 !important;
        border: 1px solid #2d3348;
    }
    .streamlit-expanderContent {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
        border: 1px solid #2d3348;
        border-top: none;
        border-radius: 0 0 6px 6px;
    }
    
    /* Alertas */
    .stAlert {
        border-radius: 6px;
        border-left: 4px solid;
        background-color: #1a1f2e !important;
        color: #e6edf3 !important;
    }
    .stSuccess {
        background-color: #1a3a2a !important;
        border-left-color: #7ee787 !important;
    }
    .stError {
        background-color: #3a1a1a !important;
        border-left-color: #ff7b72 !important;
    }
    .stWarning {
        background-color: #3a2a1a !important;
        border-left-color: #ffd966 !important;
    }
    .stInfo {
        background-color: #1a2a3a !important;
        border-left-color: #79c0ff !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1f2e !important;
        border-radius: 6px;
        padding: 8px 16px;
        color: #c9d1d9 !important;
        border: 1px solid #2d3348;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
        border: none;
    }
    
    /* Contenedores */
    div[data-testid="stBlock"] {
        background-color: transparent !important;
    }
    
    /* Columnas */
    div[data-testid="column"] {
        background-color: transparent !important;
    }
    
    /* Código */
    code {
        color: #ff7b72 !important;
        background-color: #1a1f2e !important;
        padding: 2px 4px;
        border-radius: 4px;
    }
    
    /* Dividers */
    hr {
        border-color: #2d3348 !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        color: #58a6ff !important;
    }
    
    /* Download button */
    .stDownloadButton button {
        background-color: #21262d !important;
        color: #ffffff !important;
        border: 1px solid #2d3348;
    }
    .stDownloadButton button:hover {
        background-color: #2d3348 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE UTILIDAD ---
def notificar(mensaje, tipo="info"):
    """Sistema de notificaciones"""
    if tipo == "success":
        st.toast(f"✅ {mensaje}", icon="🎉")
    elif tipo == "error":
        st.toast(f"❌ {mensaje}", icon="⚠️")
    elif tipo == "warning":
        st.toast(f"⚠️ {mensaje}", icon="📢")
    else:
        st.toast(f"ℹ️ {mensaje}", icon="📋")

def log_accion(usuario, accion, detalles):
    """Registro de acciones en log"""
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
                    ws_log.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        str(usuario),
                        accion,
                        str(detalles)
                    ])
                except:
                    pass
    except:
        pass

# --- FUNCIONES CON CACHÉ ---
@st.cache_resource(ttl=600)
def conectar_gsheet():
    """Conexión a Google Sheets"""
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except Exception as e:
        if DEBUG:
            st.error(f"Error de conexión: {str(e)}")
        return None

@st.cache_data(ttl=60)
def obtener_datos_tabla(nombre_pestaña):
    """Obtener datos de una tabla específica"""
    try:
        sheet = conectar_gsheet()
        if not sheet:
            notificar("Error de conexión con Google Sheets", "error")
            return pd.DataFrame()
        
        try:
            ws = sheet.worksheet(nombre_pestaña)
            data = ws.get_all_values()
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                df.columns = [c.strip() for c in df.columns]
                return df
            return pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            notificar(f"Hoja '{nombre_pestaña}' no encontrada", "warning")
            return pd.DataFrame()
    except Exception as e:
        notificar(f"Error al cargar {nombre_pestaña}: {str(e)[:50]}", "error")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def cargar_nomina():
    """Cargar nómina"""
    return obtener_datos_tabla("Nómina")

def guardar_registro(datos):
    """Guardar un registro directamente en Google Sheets"""
    try:
        sheet = conectar_gsheet()
        if not sheet:
            return False, "Sin conexión a Google Sheets"
        
        ws = sheet.worksheet("Registros")
        ws.append_row(list(datos.values()))
        return True, "Registro guardado exitosamente"
    except Exception as e:
        return False, f"Error al guardar: {str(e)[:100]}"

# --- INICIALIZACIÓN DE SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- MODO DEBUG ---
if DEBUG:
    st.sidebar.warning("🔧 MODO DESARROLLO ACTIVADO")

# --- LOGIN ---
if not st.session_state.logueado:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.write("")
        st.title("📟 Terminal de Acceso")
        st.markdown("---")
        with st.form("login_form"):
            u = st.text_input("Credencial (DNI)", placeholder="Ingrese su DNI")
            p = st.text_input("Código", type="password", placeholder="Contraseña")
            submitted = st.form_submit_button("🔐 AUTENTICAR", use_container_width=True)
            
            if submitted:
                if not u or not p:
                    st.error("❌ Complete todos los campos")
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
                                log_accion(u, "LOGIN_EXITOSO", "Usuario autenticado")
                                notificar(f"Bienvenido {st.session_state.user_info['nombre']}", "success")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ Acceso denegado - Credenciales inválidas")
                                log_accion(u, "LOGIN_FALLIDO", "Intento de acceso fallido")
                        except Exception as e:
                            st.error(f"Error de autenticación: {str(e)}")
                    else:
                        st.error("❌ Error de conexión con el servidor")
else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=80)
        st.markdown(f"### 👤 {st.session_state.user_info.get('nombre', 'OPERADOR')}")
        st.caption(f"Rol: {st.session_state.user_info.get('rol', 'OPERADOR')} | DNI: {st.session_state.user_info.get('dni', '---')}")
        st.write("---")
        
        if st.button("🚪 SALIR DEL SISTEMA", use_container_width=True):
            log_accion(st.session_state.user_info.get('dni', 'desconocido'), "LOGOUT", "Cierre de sesión")
            st.session_state.logueado = False
            st.session_state.user_info = {}
            notificar("Sesión cerrada correctamente", "info")
            time.sleep(0.5)
            st.rerun()
        
        with st.expander("ℹ️ Información del Sistema"):
            st.caption(f"Versión: 3.0")
            st.caption(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Título principal
    st.title("👮‍♂️ Unidad Regional V - Sistema de Carga Táctico")
    
    # Cargar datos
    with st.spinner("Cargando datos del sistema..."):
        df_nomina = cargar_nomina()
    
    # --- MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("👥 TOTAL EFECTIVOS", len(df_nomina))
    with col2:
        st.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))
    with col3:
        st.metric("👤 OPERADOR", st.session_state.user_info.get('nombre', '---')[:20])

    st.write("---")
    
    # --- FORMULARIO PRINCIPAL ---
    st.subheader("📝 Registro de Servicio")
    
    col_form, col_info = st.columns([1.5, 1], gap="large")
    
    with col_form:
        with st.form("registro_form", clear_on_submit=True):
            # Fecha
            f_in = st.date_input("📅 Fecha Servicio", datetime.now())
            f_str = f_in.strftime("%d/%m/%Y")
            
            # Búsqueda de efectivos
            search_term = st.text_input("🔍 Buscar efectivo", placeholder="Escriba nombre o DNI...")
            
            nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            if search_term:
                nombres = [n for n in nombres if search_term.lower() in n.lower()]
            
            if not nombres:
                st.warning("No se encontraron efectivos")
                agente = "---"
            else:
                agente = st.selectbox("👮 Seleccionar Personal", ["---"] + nombres)
            
            detalle = st.text_area("📝 Detalles / Observación", placeholder="Ingrese detalles del servicio...", height=100)
            
            # Botón de envío
            submitted = st.form_submit_button("✅ GUARDAR REGISTRO", type="primary", use_container_width=True)
            
            if submitted and agente != "---":
                datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                dni = str(datos['DNI'])
                dep = datos['DEPENDENCIA']
                
                registro = {
                    "FECHA": f_str,
                    "APELLIDO Y NOMBRES": agente,
                    "DNI": dni,
                    "DEPENDENCIA": dep,
                    "OBSERVACIONES": detalle if detalle else "S/O"
                }
                
                with st.spinner("Guardando registro..."):
                    success, message = guardar_registro(registro)
                    if success:
                        st.balloons()
                        notificar(message, "success")
                        log_accion(st.session_state.user_info.get('dni', 'desconocido'), 
                                  "REGISTRO_CREADO", 
                                  f"{agente} - {f_str}")
                        # Limpiar caché para actualizar datos
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            elif submitted and agente == "---":
                st.warning("⚠️ Por favor seleccione un efectivo")
    
    with col_info:
        st.subheader("📋 Últimos Registros")
        
        # Cargar registros recientes
        df_reg = obtener_datos_tabla("Registros")
        
        if not df_reg.empty:
            # Mostrar últimos 5 registros
            df_recent = df_reg.head(5)
            cols_mostrar = ['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']
            if 'OBSERVACIONES' in df_recent.columns:
                cols_mostrar.append('OBSERVACIONES')
            st.dataframe(df_recent[cols_mostrar], use_container_width=True, hide_index=True)
            
            # Estadísticas rápidas
            st.markdown("---")
            st.subheader("📊 Estadísticas Rápidas")
            
            if 'DEPENDENCIA' in df_reg.columns:
                top_dep = df_reg['DEPENDENCIA'].value_counts().head(3)
                for dep, count in top_dep.items():
                    st.metric(f"🏢 {dep}", f"{count} registros")
        else:
            st.info("No hay registros previos")
    
    # --- ESTADÍSTICAS ADICIONALES ---
    st.write("---")
    
    with st.expander("📊 Distribución de Efectivos por Dependencia"):
        if not df_nomina.empty:
            dep_count = df_nomina['DEPENDENCIA'].value_counts()
            
            # Crear columnas para mostrar en grid
            cols = st.columns(3)
            for idx, (dep, count) in enumerate(dep_count.items()):
                with cols[idx % 3]:
                    st.metric(f"🏛️ {dep}", count)

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #8b949e; font-size: 12px;'>"
    "Unidad Regional V - Sistema Táctico de Gestión de Personal | © 2024"
    "</p>", 
    unsafe_allow_html=True
)
