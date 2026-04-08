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

# --- FUNCIONES ---
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
        return True, "✅ Registro guardado"
    except Exception as e:
        return False, f"❌ Error: {str(e)[:100]}"

# --- INICIALIZACIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- LOGIN ---
if not st.session_state.logueado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("📟 Terminal de Acceso")
        st.markdown("---")
        
        with st.form("login_form"):
            usuario = st.text_input("DNI")
            clave = st.text_input("Clave", type="password")
            submitted = st.form_submit_button("🔐 INGRESAR", use_container_width=True)
            
            if submitted:
                if usuario and clave:
                    sheet = conectar_gsheet()
                    if sheet:
                        try:
                            ws_u = sheet.worksheet("Usuarios")
                            df_u = pd.DataFrame(ws_u.get_all_records())
                            match = df_u[(df_u['Usuario'].astype(str) == usuario) & (df_u['Clave'].astype(str) == clave)]
                            if not match.empty:
                                st.session_state.logueado = True
                                st.session_state.user_info = {
                                    'dni': usuario,
                                    'nombre': match.iloc[0].get('NOMBRE', usuario),
                                }
                                st.rerun()
                            else:
                                st.error("❌ Acceso denegado")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                    else:
                        st.error("❌ Error de conexión")
                else:
                    st.warning("Complete todos los campos")

else:
    # --- APP PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=80)
        st.markdown(f"### 👤 {st.session_state.user_info.get('nombre', 'OPERADOR')}")
        st.markdown("---")
        if st.button("🚪 SALIR", use_container_width=True):
            st.session_state.logueado = False
            st.session_state.user_info = {}
            st.rerun()
        st.markdown("---")
        st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Título
    st.title("👮‍♂️ Unidad Regional V")
    st.markdown("### Sistema de Carga de Servicios")
    st.markdown("---")

    # Cargar datos
    with st.spinner("Cargando personal..."):
        df_nomina = cargar_nomina()
        df_registros = obtener_datos_tabla("Registros")

    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 TOTAL EFECTIVOS", len(df_nomina))
    col2.metric("📊 REGISTROS HOY", len(df_registros[df_registros['FECHA'] == datetime.now().strftime("%d/%m/%Y")]) if not df_registros.empty else 0)
    col3.metric("👤 OPERADOR", st.session_state.user_info.get('nombre', '---'))

    st.markdown("---")

    # --- FORMULARIO PRINCIPAL ---
    col_form, col_lista = st.columns([1.2, 1])

    with col_form:
        st.subheader("📝 NUEVO REGISTRO")
        
        with st.form("registro_form", clear_on_submit=True):
            fecha = st.date_input("📅 Fecha", datetime.now())
            fecha_str = fecha.strftime("%d/%m/%Y")
            
            # Selector de personal - VERSIÓN SIMPLE
            lista_nombres = df_nomina['APELLIDO Y NOMBRES'].tolist() if not df_nomina.empty else []
            
            if lista_nombres:
                agente = st.selectbox(
                    "👮 Seleccionar Efectivo",
                    options=["-- SELECCIONE --"] + sorted(lista_nombres)
                )
            else:
                st.warning("No hay datos de personal cargados")
                agente = "-- SELECCIONE --"
            
            # Botón guardar
            guardar = st.form_submit_button("💾 GUARDAR REGISTRO", type="primary", use_container_width=True)
            
            if guardar:
                if agente and agente != "-- SELECCIONE --":
                    # Obtener datos del agente
                    datos_agente = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                    
                    registro = {
                        "FECHA": fecha_str,
                        "APELLIDO Y NOMBRES": agente,
                        "DNI": str(datos_agente['DNI']),
                        "DEPENDENCIA": datos_agente['DEPENDENCIA']
                    }
                    
                    with st.spinner("Guardando..."):
                        ok, mensaje = guardar_registro(registro)
                        if ok:
                            st.success(mensaje)
                            st.balloons()
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(mensaje)
                else:
                    st.warning("⚠️ Por favor, seleccione un efectivo")

    with col_lista:
        st.subheader("📋 ÚLTIMOS REGISTROS")
        
        if not df_registros.empty:
            # Mostrar últimos 8 registros
            ultimos = df_registros.head(8)[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']]
            st.dataframe(ultimos, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros cargados aún")

    # --- ESTADÍSTICAS ---
    st.markdown("---")
    with st.expander("📊 ESTADÍSTICAS POR DEPENDENCIA"):
        if not df_nomina.empty:
            stats = df_nomina['DEPENDENCIA'].value_counts()
            
            # Mostrar en 3 columnas
            cols = st.columns(3)
            for idx, (dep, cant) in enumerate(stats.items()):
                with cols[idx % 3]:
                    st.metric(f"🏛️ {dep}", cant)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>Unidad Regional V - Sistema de Gestión de Personal</p>",
    unsafe_allow_html=True
)
