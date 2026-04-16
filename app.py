import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import unicodedata

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

# --- FUNCIÓN PARA NORMALIZAR TEXTO (eliminar acentos y mayúsculas) ---
def normalizar_texto(texto):
    """Elimina acentos, convierte a minúsculas y quita espacios extras"""
    if pd.isna(texto) or texto is None:
        return ""
    texto = str(texto).strip().lower()
    # Eliminar acentos
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto

# --- CONEXIÓN Y CONSULTAS ---

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
    """Obtiene datos SIN usar caché"""
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

# --- FUNCIÓN PARA OBTENER HISTORIAL DEL EFECTIVO (COMPARACIÓN INTELIGENTE) ---
def obtener_historial_efectivo(df_registros, nombre_agente):
    """
    Retorna todas las fechas donde el efectivo aparece en registros.
    Compara NORMALIZANDO el texto (sin acentos, mayúsculas, espacios)
    """
    if df_registros.empty:
        return []
    
    nombre_normalizado = normalizar_texto(nombre_agente)
    fechas = []
    
    for idx, row in df_registros.iterrows():
        nombre_reg = row.get('APELLIDO Y NOMBRES', '')
        nombre_reg_normalizado = normalizar_texto(nombre_reg)
        
        if nombre_reg_normalizado == nombre_normalizado:
            fecha_reg = str(row.get('FECHA', '')).strip()
            fechas.append(fecha_reg)
    
    return fechas

# --- FUNCIÓN PARA VERIFICAR SI UN NOMBRE EXISTE EN REGISTROS ---
def efectivo_tiene_registros(df_registros, nombre_agente):
    """Retorna True si el efectivo ya tiene al menos un registro"""
    historial = obtener_historial_efectivo(df_registros, nombre_agente)
    return len(historial) > 0, historial

# --- SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'confirmar_duplicado' not in st.session_state:
    st.session_state.confirmar_duplicado = None

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
    
    # --- CARGAR DATOS ---
    with st.spinner("Cargando datos..."):
        df_nomina = obtener_datos_sin_cache("Nómina")
        df_registros = obtener_datos_sin_cache("Registros")
    
    fecha_control = datetime.now().date()
    fecha_control_str = fecha_control.strftime("%d/%m/%Y")
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
    c2.metric("📝 TOTAL CARGAS", len(df_registros))
    c3.metric("📅 FECHA", fecha_control_str)

    st.divider()
    
    # --- MODAL DE CONFIRMACIÓN ---
    if st.session_state.confirmar_duplicado:
        agente_pendiente, fecha_pendiente, historial = st.session_state.confirmar_duplicado
        
        st.error("⚠️ **EFECTIVO CON REGISTROS PREVIOS**")
        st.warning(f"El efectivo **{agente_pendiente}** ya tiene **{len(historial)} servicio(s)** registrado(s) anteriormente:")
        
        for fecha in historial:
            st.write(f"  • {fecha}")
        
        st.warning("¿Desea cargar un NUEVO servicio para este efectivo?")
        
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ SÍ, CARGAR DE TODOS MODOS", use_container_width=True):
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_pendiente].iloc[0]
                nuevo_reg = [
                    fecha_pendiente,
                    agente_pendiente,
                    str(datos_ag['DNI']),
                    datos_ag['DEPENDENCIA'],
                    f"EFECTIVO CON {len(historial)} REGISTROS PREVIOS"
                ]
                
                try:
                    sheet = conectar_gsheet()
                    ws_reg = sheet.worksheet("Registros")
                    ws_reg.append_row(nuevo_reg)
                    
                    st.cache_data.clear()
                    st.session_state.confirmar_duplicado = None
                    st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente_pendiente} guardado!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
                    st.session_state.confirmar_duplicado = None
        
        with col_no:
            if st.button("❌ NO, CANCELAR", use_container_width=True):
                st.session_state.confirmar_duplicado = None
                st.rerun()
        
        st.stop()
    
    # --- FORMULARIO PRINCIPAL ---
    col_form, col_list = st.columns([1, 1.3], gap="large")

    with col_form:
        st.subheader("📝 Nuevo Registro")
        
        with st.form("registro_form", clear_on_submit=True):
            fecha = st.date_input("Fecha", fecha_control)
            lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
            
            # --- ADVERTENCIA INMEDIATA (con comparación inteligente) ---
            if agente != "-- SELECCIONE --" and not df_registros.empty:
                tiene_registros, historial = efectivo_tiene_registros(df_registros, agente)
                if tiene_registros:
                    st.warning(f"⚠️ **ATENCIÓN:** Este efectivo ya tiene {len(historial)} servicio(s) registrado(s) anteriormente:")
                    for fecha_ant in historial[:5]:  # Mostrar máximo 5
                        st.write(f"  • {fecha_ant}")
                    if len(historial) > 5:
                        st.write(f"  • ... y {len(historial) - 5} más")
                    st.info("Puedes continuar con la carga. Se te pedirá confirmación final.")
            
            submitted = st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True)
            
            if submitted:
                if agente == "-- SELECCIONE --":
                    st.warning("Seleccione un agente.")
                else:
                    # Verificar historial con comparación inteligente
                    tiene_registros, historial = efectivo_tiene_registros(df_registros, agente)
                    
                    if tiene_registros:
                        st.session_state.confirmar_duplicado = (agente, fecha.strftime("%d/%m/%Y"), historial)
                        st.rerun()
                    else:
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
            
            if 'agente' in locals() and agente != "-- SELECCIONE --":
                _, historial = efectivo_tiene_registros(df_registros, agente)
                if historial:
                    with st.expander(f"📜 Historial completo de {agente}"):
                        for fecha in historial:
                            st.write(f"• {fecha}")
        else:
            st.info("No hay registros en el sistema")

    st.caption("✅ **Control inteligente:** Compara ignorando acentos, mayúsculas y espacios")
