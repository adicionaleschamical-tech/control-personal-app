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

@st.cache_data(ttl=60)
def obtener_datos(nombre_pestaña):
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
    except:
        return pd.DataFrame()

# --- FUNCIÓN PARA VERIFICAR SI EL EFECTIVO YA HIZO SERVICIO EN ESA FECHA ---
def efectivo_ya_registrado(df_registros, nombre_agente, fecha_servicio):
    """
    Verifica en TODOS los registros históricos (no solo los mostrados)
    si el efectivo ya tiene un registro en la fecha especificada.
    """
    if df_registros.empty:
        return False
    
    # Formatear la fecha a comparar
    fecha_str = fecha_servicio.strftime("%d/%m/%Y")
    
    # Limpiar posibles espacios en blanco en los nombres
    df_temp = df_registros.copy()
    df_temp['FECHA'] = df_temp['FECHA'].astype(str).str.strip()
    df_temp['APELLIDO Y NOMBRES'] = df_temp['APELLIDO Y NOMBRES'].astype(str).str.strip()
    nombre_agente_clean = nombre_agente.strip()
    
    # Buscar coincidencias exactas
    coincidencias = df_temp[
        (df_temp['FECHA'] == fecha_str) & 
        (df_temp['APELLIDO Y NOMBRES'] == nombre_agente_clean)
    ]
    
    return len(coincidencias) > 0

# --- SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None

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
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.write(f"**Operador:** {st.session_state.user_info['nombre']}")
        if st.button("🚪 CERRAR SESIÓN"):
            st.session_state.logueado = False
            st.session_state.user_info = {}
            st.session_state.mensaje_exito = None
            st.rerun()

    st.title("👮‍♂️ Carga de Servicios - UR-V")
    
    # Mostrar mensaje de éxito si existe
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.balloons()
        st.session_state.mensaje_exito = None
    
    # Carga de datos
    df_nomina = obtener_datos("Nómina")
    df_registros = obtener_datos("Registros")

    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
    c2.metric("📝 TOTAL CARGAS", len(df_registros))
    c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))

    st.divider()

    col_form, col_list = st.columns([1, 1.3], gap="large")

    with col_form:
        st.subheader("📝 Nuevo Registro")
        
        # Mostrar información de verificación
        if not df_registros.empty:
            st.caption(f"🔍 Verificando duplicados en {len(df_registros)} registros históricos")
        
        with st.form("registro_form", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.now())
            lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
            
            if st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True):
                if agente != "-- SELECCIONE --":
                    
                    # --- VERIFICACIÓN DE DUPLICADO (revisando TODOS los registros) ---
                    if efectivo_ya_registrado(df_registros, agente, fecha):
                        st.error(f"⚠️ El efectivo **{agente}** ya tiene un registro cargado para el **{fecha.strftime('%d/%m/%Y')}**")
                        st.info("No se permite cargar dos servicios del mismo efectivo en la misma fecha.")
                    else:
                        datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                        
                        # Preparamos el registro
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
                            
                            # Limpiar caché de datos
                            st.cache_data.clear()
                            
                            # Guardar mensaje de éxito en session_state
                            st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente} guardado!"
                            
                            # Recargar la página para actualizar datos pero mantener sesión
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                else:
                    st.warning("Seleccione un agente.")

    with col_list:
        st.subheader("📋 Últimos Servicios Cargados")
        if not df_registros.empty:
            # Mostramos las columnas principales (ordenadas por fecha descendente)
            df_visualizar = df_registros.sort_values('FECHA', ascending=False).head(10)
            
            st.dataframe(
                df_visualizar[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']], 
                use_container_width=True, 
                hide_index=True
            )
            
            if st.button("🔄 REFRESCAR LISTA"):
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("No hay registros recientes.")

    st.caption("Sistema de carga de servicios - Verifica duplicados en todos los registros históricos")
