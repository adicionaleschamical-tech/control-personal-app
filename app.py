import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Regional V - Sistema de Carga",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetricValue"] { color: #58a6ff; font-weight: bold; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource(ttl=600)
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

# --- FUNCIONES DE LECTURA ---
def leer_registros(sheet):
    try:
        ws_registros = sheet.worksheet("Registros")
        data_registros = ws_registros.get_all_values()
        if len(data_registros) > 1:
            df = pd.DataFrame(data_registros[1:], columns=data_registros[0])
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def leer_nomina(sheet):
    try:
        ws_nomina = sheet.worksheet("Nómina")
        data_nomina = ws_nomina.get_all_values()
        if len(data_nomina) > 1:
            df = pd.DataFrame(data_nomina[1:], columns=data_nomina[0])
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def leer_usuarios(sheet):
    """Lee la hoja Usuarios - adaptado a la estructura real"""
    try:
        ws_usuarios = sheet.worksheet("Usuarios")
        data = ws_usuarios.get_all_values()
        if len(data) > 1:
            # Limpiar headers
            headers = [str(h).strip().upper() for h in data[0]]
            df = pd.DataFrame(data[1:], columns=headers)
            # Limpiar valores
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer Usuarios: {e}")
        return pd.DataFrame()

# --- FUNCIÓN DE CIERRE DE MES ---
def cerrar_mes(sheet):
    try:
        ws_registros = sheet.worksheet("Registros")
        data = ws_registros.get_all_values()
        
        if len(data) <= 1:
            return False, "No hay datos para archivar."

        nombre_historico = f"Backup_{datetime.now().strftime('%m_%Y_%H%M')}"
        nueva_ws = sheet.add_worksheet(title=nombre_historico, rows=len(data), cols=len(data[0]))
        nueva_ws.update(data)
        
        headers = [data[0]]
        ws_registros.clear()
        ws_registros.update(headers, 'A1')
        
        return True, f"Mes cerrado. Historial guardado como: {nombre_historico}"
    except Exception as e:
        return False, f"Error al cerrar mes: {str(e)}"

# --- INICIALIZAR SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'confirmar_carga' not in st.session_state:
    st.session_state.confirmar_carga = None

# --- LOGIN ---
if not st.session_state.logueado:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.title("🔐 Acceso Sistema")
        with st.form("login"):
            u = st.text_input("USUARIO")
            p = st.text_input("CLAVE", type="password")
            if st.form_submit_button("INGRESAR", use_container_width=True):
                sheet = conectar_gsheet()
                if sheet:
                    df_u = leer_usuarios(sheet)
                    
                    # Mostrar debug para verificar columnas
                    st.write("🔍 Columnas encontradas:", df_u.columns.tolist())
                    st.dataframe(df_u.head(3))
                    
                    # Buscar con nombres correctos
                    if 'USUARIO' in df_u.columns and 'CLAVE' in df_u.columns:
                        match = df_u[(df_u['USUARIO'] == u) & (df_u['CLAVE'] == p)]
                        if not match.empty:
                            st.session_state.logueado = True
                            st.session_state.user_info = {
                                'dni': u, 
                                'nombre': u,
                                'dependencia': match.iloc[0].get('DEPENDENCIA', ''),
                                'rol': match.iloc[0].get('ROL', 'USUARIO')
                            }
                            st.rerun()
                        else:
                            st.error("USUARIO o CLAVE incorrectos")
                    else:
                        st.error(f"Columnas requeridas no encontradas. Columnas disponibles: {df_u.columns.tolist()}")
                else:
                    st.error("Error de conexión a Google Sheets")
else:
    # --- APP PRINCIPAL ---
    sheet = conectar_gsheet()
    if sheet is None:
        st.stop()
    
    df_nomina = leer_nomina(sheet)
    df_registros = leer_registros(sheet)
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.write(f"**Operador:** {st.session_state.user_info['nombre']}")
        st.write(f"**Rol:** {st.session_state.user_info.get('rol', 'USUARIO')}")
        
        st.divider()
        
        # Herramientas de Administrador
        st.subheader("⚙️ Administración")
        with st.expander("Finalizar Período"):
            st.info("Esta acción moverá los registros a una hoja nueva y vaciará la tabla actual.")
            if st.button("🚀 CERRAR MES", use_container_width=True):
                exito, msg = cerrar_mes(sheet)
                if exito:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)

        st.divider()
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.title("👮‍♂️ Carga de Servicios - UR-V")
    
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.session_state.mensaje_exito = None
    
    # --- MODAL DE CONFIRMACIÓN DE DUPLICADO ---
    if st.session_state.confirmar_carga:
        agente, fecha, fechas_previas = st.session_state.confirmar_carga
        st.warning(f"⚠️ **{agente} YA TIENE {len(fechas_previas)} REGISTRO(S)**")
        st.info("¿Desea cargar otro servicio de todas formas?")
        
        c_si, c_no = st.columns(2)
        with c_si:
            if st.button("✅ SÍ, CARGAR", use_container_width=True):
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                nuevo_reg = [fecha, agente, str(datos_ag['DNI']), datos_ag['DEPENDENCIA'], "CARGA EXTRA"]
                sheet.worksheet("Registros").append_row(nuevo_reg)
                st.session_state.confirmar_carga = None
                st.session_state.mensaje_exito = f"✅ Servicio guardado para {agente}"
                st.rerun()
        with c_no:
            if st.button("❌ CANCELAR", use_container_width=True):
                st.session_state.confirmar_carga = None
                st.rerun()
        st.stop()

    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
    c2.metric("📝 TOTAL CARGAS", len(df_registros))
    c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))
    
    st.divider()
    
    # --- FORMULARIO ---
    col_form, col_list = st.columns([1, 1.3], gap="large")
    
    with col_form:
        st.subheader("📝 Nuevo Registro")
        with st.form("registro_form", clear_on_submit=True):
            f_input = st.date_input("Fecha", datetime.now())
            lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            agente_sel = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
            
            submitted = st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True)
            
            if submitted:
                if agente_sel == "-- SELECCIONE --":
                    st.warning("Seleccione un agente")
                else:
                    existe = (df_registros['APELLIDO Y NOMBRES'] == agente_sel).any() if not df_registros.empty else False
                    if existe:
                        previas = df_registros[df_registros['APELLIDO Y NOMBRES'] == agente_sel]['FECHA'].tolist()
                        st.session_state.confirmar_carga = (agente_sel, f_input.strftime("%d/%m/%Y"), previas)
                        st.rerun()
                    else:
                        datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel].iloc[0]
                        nuevo_reg = [f_input.strftime("%d/%m/%Y"), agente_sel, str(datos_ag['DNI']), datos_ag['DEPENDENCIA'], ""]
                        sheet.worksheet("Registros").append_row(nuevo_reg)
                        st.session_state.mensaje_exito = f"✅ Servicio de {agente_sel} guardado!"
                        st.rerun()
    
    with col_list:
        st.subheader("📋 Últimos Servicios")
        if not df_registros.empty:
            st.dataframe(df_registros.tail(10), use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros recientes.")
