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
    except:
        return None

# --- FUNCIONES PARA LEER DATOS ---
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
                        st.session_state.confirmar_carga = None
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
else:
    # --- APP PRINCIPAL ---
    sheet = conectar_gsheet()
    
    # Leer datos frescos
    df_nomina = leer_nomina(sheet)
    df_registros = leer_registros(sheet)
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.write(f"**Operador:** {st.session_state.user_info['nombre']}")
        
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.title("👮‍♂️ Carga de Servicios - UR-V")
    
    # Mensaje de éxito
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.balloons()
        st.session_state.mensaje_exito = None
    
    # --- MODAL DE CONFIRMACIÓN (si hay que confirmar) ---
    if st.session_state.confirmar_carga:
        agente, fecha, fechas_previas = st.session_state.confirmar_carga
        
        st.warning(f"⚠️ **EL EFECTIVO {agente} YA TIENE {len(fechas_previas)} SERVICIO(S) PREVIO(S)**")
        st.write("Fechas anteriores:")
        for f in fechas_previas[:5]:
            st.write(f"  • {f}")
        if len(fechas_previas) > 5:
            st.write(f"  • ... y {len(fechas_previas)-5} más")
        
        st.info("¿Desea cargar otro servicio para este efectivo de todas formas?")
        
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ SÍ, CARGAR DE TODOS MODOS", use_container_width=True):
                # Guardar el registro
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                nuevo_reg = [
                    fecha,
                    agente,
                    str(datos_ag['DNI']),
                    datos_ag['DEPENDENCIA'],
                    f"CARGA AUTORIZADA - EFECTIVO CON {len(fechas_previas)} REGISTROS PREVIOS"
                ]
                
                try:
                    ws_reg = sheet.worksheet("Registros")
                    ws_reg.append_row(nuevo_reg)
                    st.session_state.confirmar_carga = None
                    st.session_state.mensaje_exito = f"✅ ¡Servicio de {agente} guardado!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
                    st.session_state.confirmar_carga = None
        
        with col_no:
            if st.button("❌ NO, CANCELAR", use_container_width=True):
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
            fecha = st.date_input("Fecha", datetime.now())
            lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
            
            # --- ADVERTENCIA INMEDIATA (solo informativa, NO bloquea) ---
            if agente != "-- SELECCIONE --" and not df_registros.empty:
                existe = (df_registros['APELLIDO Y NOMBRES'] == agente).any()
                
                if existe:
                    fechas = df_registros[df_registros['APELLIDO Y NOMBRES'] == agente]['FECHA'].tolist()
                    st.warning(f"⚠️ **ATENCIÓN:** Este efectivo ya tiene {len(fechas)} servicio(s) previo(s)")
                    with st.expander("Ver fechas anteriores"):
                        for f in fechas:
                            st.write(f"  • {f}")
            
            submitted = st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True)
            
            if submitted:
                if agente == "-- SELECCIONE --":
                    st.warning("Seleccione un agente")
                else:
                    # Verificar si ya existe para mostrar confirmación
                    df_registros_fresco = leer_registros(sheet)
                    existe = (df_registros_fresco['APELLIDO Y NOMBRES'] == agente).any()
                    
                    if existe:
                        # Obtener fechas previas
                        fechas_previas = df_registros_fresco[df_registros_fresco['APELLIDO Y NOMBRES'] == agente]['FECHA'].tolist()
                        # Guardar en sesión para mostrar modal
                        st.session_state.confirmar_carga = (agente, fecha.strftime("%d/%m/%Y"), fechas_previas)
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
            st.info("No hay registros recientes.")
    
    st.caption("✅ **Control activo:** Se advierte si el efectivo ya tiene registros, pero se permite cargar nuevamente si se confirma")
