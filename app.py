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

# --- ESTILO TÁCTICO OSCURO ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetricValue"] { color: #58a6ff; font-weight: bold; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    div[data-testid="stAlert"] { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN Y CONSULTAS OPTIMIZADAS ---

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

def obtener_datos_sin_cache(nombre_pestaña):
    """Obtiene datos SIN usar caché para asegurar datos actualizados"""
    try:
        sheet = conectar_gsheet()
        if not sheet: return pd.DataFrame()
        ws = sheet.worksheet(nombre_pestaña)
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

# --- FUNCIÓN PARA VERIFICAR SI EL EFECTIVO YA EXISTE EN REGISTROS (CUALQUIER FECHA) ---
def efectivo_ya_registrado(df_registros, nombre_agente):
    """
    Verifica si el efectivo ya aparece en la columna B (APELLIDO Y NOMBRES)
    en CUALQUIER fecha del registro histórico
    """
    if df_registros.empty:
        return False, None
    
    nombre_clean = nombre_agente.strip()
    
    # Buscar todas las coincidencias
    registros_anteriores = []
    for idx, row in df_registros.iterrows():
        nombre_reg = str(row.get('APELLIDO Y NOMBRES', '')).strip()
        
        if nombre_reg == nombre_clean:
            fecha_reg = str(row.get('FECHA', '')).strip()
            registros_anteriores.append(fecha_reg)
    
    if len(registros_anteriores) > 0:
        return True, registros_anteriores
    else:
        return False, None

# --- SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'confirmar_duplicado' not in st.session_state:
    st.session_state.confirmar_duplicado = None  # Guardará (agente, fecha, registros_previos)

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
                        st.session_state.mensaje_exito = None
                        st.session_state.confirmar_duplicado = None
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.write(f"**Operador:** {st.session_state.user_info['nombre']}")
        
        if st.button("🔄 ACTUALIZAR DATOS", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.logueado = False
            st.session_state.user_info = {}
            st.session_state.mensaje_exito = None
            st.session_state.confirmar_duplicado = None
            st.rerun()

    st.title("👮‍♂️ Carga de Servicios - UR-V")
    
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.balloons()
        st.session_state.mensaje_exito = None
    
    # --- CARGAR DATOS ACTUALIZADOS ---
    with st.spinner("Cargando datos..."):
        df_nomina = obtener_datos_sin_cache("Nómina")
        df_registros = obtener_datos_sin_cache("Registros")
    
    # Fecha actual
    fecha_control = datetime.now().date()
    fecha_control_str = fecha_control.strftime("%d/%m/%Y")
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
    c2.metric("📝 TOTAL CARGAS", len(df_registros))
    c3.metric("📅 FECHA", fecha_control_str)

    st.divider()
    
    # --- MOSTRAR CONFIRMACIÓN SI HAY UN DUPLICADO PENDIENTE (efectivo ya existe en registros) ---
    if st.session_state.confirmar_duplicado:
        agente_pendiente, fecha_pendiente, registros_previos = st.session_state.confirmar_duplicado
        
        st.error("⚠️ **ADVERTENCIA: EFECTIVO YA REGISTRADO EN EL SISTEMA**")
        st.warning(f"El efectivo **{agente_pendiente}** ya aparece en los registros históricos en la(s) siguiente(s) fecha(s):")
        
        for fecha in registros_previos:
            st.write(f"  • {fecha}")
        
        st.warning("¿Está seguro de que desea cargar un NUEVO servicio para este efectivo?")
        
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ SÍ, CONFIRMAR CARGA", use_container_width=True):
                # Proceder a guardar
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_pendiente].iloc[0]
                nuevo_reg = [
                    fecha_pendiente,
                    agente_pendiente,
                    str(datos_ag['DNI']),
                    datos_ag['DEPENDENCIA'],
                    "EFECTIVO CON REGISTROS PREVIOS - CARGA AUTORIZADA"
                ]
                
                try:
                    sheet = conectar_gsheet()
                    ws_reg = sheet.worksheet("Registros")
                    ws_reg.append_row(nuevo_reg)
                    
                    st.cache_data.clear()
                    st.session_state.confirmar_duplicado = None
                    st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente_pendiente} guardado correctamente!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
                    st.session_state.confirmar_duplicado = None
        
        with col_no:
            if st.button("❌ NO, CANCELAR CARGA", use_container_width=True):
                st.session_state.confirmar_duplicado = None
                st.rerun()
        
        st.stop()  # Detener la ejecución aquí mientras se muestra la confirmación

    # --- FORMULARIO PRINCIPAL ---
    col_form, col_list = st.columns([1, 1.3], gap="large")

    with col_form:
        st.subheader("📝 Nuevo Registro")
        
        with st.form("registro_form", clear_on_submit=True):
            fecha = st.date_input("Fecha", fecha_control)
            lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
            
            submitted = st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True)
            
            if submitted:
                if agente == "-- SELECCIONE --":
                    st.warning("Seleccione un agente.")
                else:
                    # VERIFICAR SI EL EFECTIVO YA EXISTE EN REGISTROS (CUALQUIER FECHA)
                    ya_registrado, fechas_previas = efectivo_ya_registrado(df_registros, agente)
                    
                    if ya_registrado:
                        # Guardar en sesión la confirmación pendiente
                        st.session_state.confirmar_duplicado = (agente, fecha.strftime("%d/%m/%Y"), fechas_previas)
                        st.rerun()
                    else:
                        # Guardar directamente (efectivo nuevo)
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
                            
                            st.cache_data.clear()
                            st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente} guardado correctamente!"
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
            st.caption(f"Total registros históricos: {len(df_registros)}")
        else:
            st.info("No hay registros en el sistema")

    st.caption("✅ **Control activo:** Si el efectivo YA EXISTE en registros históricos, se mostrará una advertencia antes de guardar")
