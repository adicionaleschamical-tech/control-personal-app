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
    div[data-testid="stAlert"] { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
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

# --- FUNCIÓN PARA LEER DATOS (SIN CACHÉ PARA REGISTROS) ---
def leer_registros():
    """Lee la pestaña Registros directamente"""
    try:
        sheet = conectar_gsheet()
        if not sheet: return pd.DataFrame()
        ws = sheet.worksheet("Registros")
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer registros: {e}")
        return pd.DataFrame()

def leer_nomina():
    """Lee la pestaña Nómina"""
    try:
        sheet = conectar_gsheet()
        if not sheet: return pd.DataFrame()
        ws = sheet.worksheet("Nómina")
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer nómina: {e}")
        return pd.DataFrame()

# --- FUNCIÓN PARA VERIFICAR SI EL EFECTIVO YA EXISTE ---
def efectivo_ya_registrado(df_registros, nombre_agente):
    """Verifica si el nombre del efectivo existe en la columna APELLIDO Y NOMBRES"""
    if df_registros.empty:
        return False, []
    
    # Buscar coincidencias EXACTAS
    coincidencias = df_registros[df_registros['APELLIDO Y NOMBRES'] == nombre_agente]
    
    if len(coincidencias) > 0:
        fechas = coincidencias['FECHA'].tolist()
        return True, fechas
    else:
        return False, []

# --- SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'pendiente_confirmacion' not in st.session_state:
    st.session_state.pendiente_confirmacion = None

# --- LOGIN ---
if not st.session_state.logueado:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.title("🔐 Acceso Sistema")
        with st.form("login"):
            u = st.text_input("DNI")
            p = st.text_input("Clave", type="password")
            if st.form_submit_button("INGRESAR", use_container_width=True):
                sheet = conectar_gsheet()
                if sheet:
                    df_u = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                    match = df_u[(df_u['Usuario'].astype(str) == u) & (df_u['Clave'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.logueado = True
                        st.session_state.user_info = {'dni': u, 'nombre': match.iloc[0].get('NOMBRE', u)}
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.write(f"**Operador:** {st.session_state.user_info['nombre']}")
        
        if st.button("🔄 ACTUALIZAR", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.logueado = False
            st.session_state.pendiente_confirmacion = None
            st.rerun()

    st.title("👮‍♂️ Carga de Servicios - UR-V")
    
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.balloons()
        st.session_state.mensaje_exito = None
    
    # --- CARGAR DATOS (SIEMPRE FRESCOS) ---
    with st.spinner("Cargando datos..."):
        df_registros = leer_registros()
        df_nomina = leer_nomina()
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
    c2.metric("📝 TOTAL CARGAS", len(df_registros))
    c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))
    
    st.divider()
    
    # --- MODAL DE CONFIRMACIÓN ---
    if st.session_state.pendiente_confirmacion:
        agente, fecha, fechas_previas = st.session_state.pendiente_confirmacion
        
        st.error("⚠️ **EFECTIVO YA REGISTRADO**")
        st.warning(f"El efectivo **{agente}** ya aparece en los registros históricos en la(s) siguiente(s) fecha(s):")
        for f in fechas_previas:
            st.write(f"  • {f}")
        
        st.warning("¿Desea cargar otro servicio para este efectivo?")
        
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ SÍ, CARGAR IGUAL", use_container_width=True):
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                nuevo_reg = [
                    fecha,
                    agente,
                    str(datos_ag['DNI']),
                    datos_ag['DEPENDENCIA'],
                    "CARGA AUTORIZADA - EFECTIVO CON REGISTROS PREVIOS"
                ]
                
                try:
                    sheet = conectar_gsheet()
                    ws_reg = sheet.worksheet("Registros")
                    ws_reg.append_row(nuevo_reg)
                    st.session_state.pendiente_confirmacion = None
                    st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente} guardado!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.pendiente_confirmacion = None
        
        with col_no:
            if st.button("❌ NO, CANCELAR", use_container_width=True):
                st.session_state.pendiente_confirmacion = None
                st.rerun()
        
        st.stop()
    
    # --- FORMULARIO PRINCIPAL ---
    col_form, col_list = st.columns([1, 1.3], gap="large")
    
    with col_form:
        st.subheader("📝 Nuevo Registro")
        
        with st.form("registro_form", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.now())
            lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
            
            # MOSTRAR ADVERTENCIA INMEDIATA si el efectivo ya existe
            if agente != "-- SELECCIONE --" and not df_registros.empty:
                existe, fechas = efectivo_ya_registrado(df_registros, agente)
                if existe:
                    st.warning(f"⚠️ **ATENCIÓN:** Este efectivo ya tiene {len(fechas)} servicio(s) previo(s)")
                    with st.expander("Ver fechas anteriores"):
                        for f in fechas:
                            st.write(f"• {f}")
            
            submitted = st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True)
            
            if submitted:
                if agente == "-- SELECCIONE --":
                    st.warning("Seleccione un agente")
                else:
                    # VERIFICAR si ya existe
                    existe, fechas_previas = efectivo_ya_registrado(df_registros, agente)
                    
                    if existe:
                        # Pedir confirmación
                        st.session_state.pendiente_confirmacion = (agente, fecha.strftime("%d/%m/%Y"), fechas_previas)
                        st.rerun()
                    else:
                        # Guardar directamente
                        datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                        nuevo_reg = [
                            fecha.strftime("%d/%m/%Y"),
                            agente,
                            str(datos_ag['DNI']),
                            datos_ag['DEPENDENCIA'],
                            ""
                        ]
                        
                        try:
                            sheet = conectar_gsheet()
                            ws_reg = sheet.worksheet("Registros")
                            ws_reg.append_row(nuevo_reg)
                            st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente} guardado!"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
    
    with col_list:
        st.subheader("📋 Últimos Servicios Cargados")
        if not df_registros.empty:
            df_visualizar = df_registros.sort_values('FECHA', ascending=False).head(10)
            st.dataframe(
                df_visualizar[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay registros")
    
    st.caption("✅ Si el efectivo YA EXISTE en registros, se mostrará advertencia antes de guardar")
