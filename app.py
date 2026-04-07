import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import os
from streamlit import runtime

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

# --- SKIN: DARK TACTICAL MODE (CSS MEJORADO) ---
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
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-family: 'Courier New', Courier, monospace;
        font-size: 2rem !important;
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
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(88, 166, 255, 0.2);
    }
    
    /* Botón Guardar (Azul Brillante) */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #1f6feb;
        color: white;
        border: none;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #388bfd;
    }
    
    /* Botón Peligro */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #da3633;
        color: white;
    }
    div.stButton > button:first-child[kind="secondary"]:hover {
        background-color: #f85149;
    }
    
    /* Tablas estilo Dark */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 10px;
    }
    .dataframe {
        font-size: 14px;
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
        border-radius: 6px !important;
    }
    input:focus, select:focus, textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1c212d;
        border-radius: 6px;
        color: #58a6ff;
    }
    
    /* Alertas personalizadas */
    .stAlert {
        border-radius: 6px;
        border-left: 4px solid;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1c212d;
        border-radius: 6px;
        padding: 8px 16px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE UTILIDAD ---
def notificar(mensaje, tipo="info"):
    """Sistema de notificaciones no bloqueantes"""
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
                # Si no existe la hoja Logs, la creamos
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
                    pass  # No crítico si falla el log
    except:
        pass  # No crítico si falla el log

# --- FUNCIONES CON CACHÉ (EVITAR ERROR 429) ---
@st.cache_resource(ttl=600)
def conectar_gsheet():
    """Conexión a Google Sheets con manejo de errores"""
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
    """Cargar nómina con caché más largo"""
    return obtener_datos_tabla("Nómina")

@st.cache_data(ttl=60)
def cargar_registros_recientes():
    """Cargar registros recientes (últimos 90 días) para mejor performance"""
    df = obtener_datos_tabla("Registros")
    if not df.empty and 'FECHA' in df.columns:
        try:
            # Convertir fechas y filtrar últimos 90 días
            df['FECHA_DT'] = pd.to_datetime(df['FECHA'], format='%d/%m/%Y', errors='coerce')
            fecha_limite = datetime.now() - pd.Timedelta(days=90)
            df = df[df['FECHA_DT'] >= fecha_limite]
            df = df.drop('FECHA_DT', axis=1)
        except:
            pass
    return df

def guardar_en_google(registros):
    """Guardar registros en Google Sheets con validación"""
    try:
        sheet = conectar_gsheet()
        if not sheet:
            return False, "Sin conexión a Google Sheets"
        
        ws = sheet.worksheet("Registros")
        for row in registros:
            ws.append_row(list(row.values()))
        return True, "Datos transmitidos exitosamente"
    except Exception as e:
        return False, f"Error en transmisión: {str(e)[:100]}"

# --- INICIALIZACIÓN DE SESIÓN ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'offline_backup' not in st.session_state:
    st.session_state.offline_backup = []

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
        
        # Mostrar última sincronización
        if st.session_state.last_sync:
            st.caption(f"🕐 Última sincronización: {st.session_state.last_sync}")
        
        st.write("---")
        if st.button("🚪 SALIR DEL SISTEMA", use_container_width=True):
            log_accion(st.session_state.user_info.get('dni', 'desconocido'), "LOGOUT", "Cierre de sesión")
            st.session_state.logueado = False
            st.session_state.lista_temporal = []
            st.session_state.user_info = {}
            notificar("Sesión cerrada correctamente", "info")
            time.sleep(0.5)
            st.rerun()
        
        # Información del sistema
        with st.expander("ℹ️ Información del Sistema"):
            st.caption(f"Versión: 2.0")
            st.caption(f"Entorno: {ENV.upper()}")
            st.caption(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Título principal
    st.title("👮‍♂️ Unidad Regional V - Sistema de Carga Táctico")
    
    # Cargar datos
    with st.spinner("Cargando datos del sistema..."):
        df_nomina = cargar_nomina()
        df_reg = cargar_registros_recientes()
    
    # --- MÉTRICAS MEJORADAS ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 EN COLA", len(st.session_state.lista_temporal))
    with col2:
        st.metric("👥 EFECTIVOS", len(df_nomina))
    with col3:
        registros_hoy = 0
        if not df_reg.empty and 'FECHA' in df_reg.columns:
            fecha_hoy = datetime.now().strftime("%d/%m/%Y")
            registros_hoy = len(df_reg[df_reg['FECHA'] == fecha_hoy])
        st.metric("📊 REGISTROS HOY", registros_hoy)
    with col4:
        st.metric("🔄 ÚLTIMA SINCRONIZACIÓN", st.session_state.last_sync or "Pendiente")

    st.write("---")
    
    # --- PESTAÑAS PARA MEJOR ORGANIZACIÓN ---
    tab1, tab2, tab3 = st.tabs(["📥 CARGA DE DATOS", "📑 COLA DE TRANSMISIÓN", "📊 CONSULTAS Y REPORTES"])
    
    with tab1:
        col_a, col_b = st.columns([1, 1.2], gap="large")
        
        with col_a:
            st.subheader("📝 Registro de Servicio")
            
            # Fecha
            f_in = st.date_input("📅 Fecha Servicio", datetime.now())
            f_str = f_in.strftime("%d/%m/%Y")
            
            # Búsqueda de efectivos
            st.markdown("#### 👮 Selección de Personal")
            search_term = st.text_input("🔍 Buscar efectivo", placeholder="Escriba nombre o DNI...")
            
            nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
            if search_term:
                nombres = [n for n in nombres if search_term.lower() in n.lower()]
            
            if not nombres:
                st.warning("No se encontraron efectivos")
                agente = "---"
            else:
                agente = st.selectbox("Seleccionar Personal", ["---"] + nombres)
            
            detalle = st.text_area("📝 Detalles / Observación", placeholder="Ingrese detalles del servicio...", height=100)
            
            if agente != "---":
                datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                dni = str(datos['DNI'])
                dep = datos['DEPENDENCIA']
                
                # Mostrar información del efectivo seleccionado
                st.info(f"**DNI:** {dni} | **Dependencia:** {dep}")
                
                # Alerta de Duplicado mejorada
                if not df_reg.empty and 'DNI' in df_reg.columns:
                    previos = df_reg[df_reg['DNI'].astype(str) == dni]
                    if not previos.empty:
                        st.warning(f"⚠️ REGISTRO EXISTENTE PARA {agente}")
                        ultimo_servicio = previos.iloc[0]['FECHA'] if 'FECHA' in previos.columns else "N/A"
                        st.caption(f"📅 Último servicio: {ultimo_servicio}")
                        with st.expander(f"📜 Ver historial completo ({len(previos)} registros)"):
                            cols_mostrar = ['FECHA', 'DEPENDENCIA', 'OBSERVACIONES'] if 'OBSERVACIONES' in previos.columns else ['FECHA', 'DEPENDENCIA']
                            st.dataframe(previos[cols_mostrar].head(10), use_container_width=True, hide_index=True)
                
                # Botón agregar
                if st.button("✚ AGREGAR A LA COLA", type="primary", use_container_width=True):
                    # Validar duplicado en cola temporal
                    if any(item['DNI'] == dni for item in st.session_state.lista_temporal):
                        notificar(f"{agente} ya está en la cola de carga", "warning")
                    else:
                        st.session_state.lista_temporal.append({
                            "FECHA": f_str, 
                            "APELLIDO Y NOMBRES": agente,
                            "DNI": dni, 
                            "DEPENDENCIA": dep, 
                            "OBSERVACIONES": detalle if detalle else "S/O"
                        })
                        notificar(f"{agente} agregado a la cola", "success")
                        time.sleep(0.5)
                        st.rerun()
            
            # Mostrar estadísticas de dependencia
            if not df_nomina.empty:
                with st.expander("📊 Estadísticas por Dependencia"):
                    dep_count = df_nomina['DEPENDENCIA'].value_counts()
                    st.dataframe(dep_count.rename("Cantidad"), use_container_width=True)
        
        with col_b:
            st.subheader("📋 Vista Previa - Últimos Registros")
            if not df_reg.empty:
                # Mostrar últimos 10 registros
                df_recent = df_reg.head(10)
                cols_mostrar = ['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']
                if 'OBSERVACIONES' in df_recent.columns:
                    cols_mostrar.append('OBSERVACIONES')
                st.dataframe(df_recent[cols_mostrar], use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros previos")
    
    with tab2:
        st.subheader("📑 Cola de Impresión/Carga")
        
        if st.session_state.lista_temporal:
            df_temp = pd.DataFrame(st.session_state.lista_temporal)
            st.dataframe(df_temp, use_container_width=True, hide_index=True)
            
            # Mostrar resumen
            st.caption(f"Total en cola: {len(st.session_state.lista_temporal)} registros")
            
            # Botones de acción
            c1, c2, c3 = st.columns(3)
            
            with c1:
                if st.button("🚀 TRANSMITIR DATOS", type="primary", use_container_width=True):
                    with st.spinner("Transmitiendo datos a Google Sheets..."):
                        success, message = guardar_en_google(st.session_state.lista_temporal)
                        if success:
                            # Guardar backup local
                            df_backup = pd.DataFrame(st.session_state.lista_temporal)
                            df_backup.to_csv(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
                            
                            st.balloons()
                            notificar(message, "success")
                            log_accion(st.session_state.user_info.get('dni', 'desconocido'), 
                                      "TRANSMISION_MASIVA", 
                                      f"{len(st.session_state.lista_temporal)} registros transmitidos")
                            
                            st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
                            st.session_state.lista_temporal = []
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            notificar(message, "error")
                            # Ofrecer guardar backup local
                            if st.button("💾 Guardar backup local"):
                                df_backup = pd.DataFrame(st.session_state.lista_temporal)
                                df_backup.to_csv(f"cola_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
                                notificar("Backup guardado localmente", "success")
            
            with c2:
                if st.button("📥 DESCARGAR COLA (CSV)", use_container_width=True):
                    df_temp = pd.DataFrame(st.session_state.lista_temporal)
                    csv = df_temp.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Click para descargar",
                        data=csv,
                        file_name=f"cola_carga_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with c3:
                if st.button("🗑️ ABORTAR CARGA", type="secondary", use_container_width=True):
                    if st.checkbox("Confirmar eliminación de toda la cola"):
                        st.session_state.lista_temporal = []
                        notificar("Cola eliminada", "warning")
                        st.rerun()
        else:
            st.info("📭 No hay datos en la cola de carga.")
            st.caption("Use la pestaña 'CARGA DE DATOS' para agregar registros")
    
    with tab3:
        st.subheader("📊 Consultas y Reportes")
        
        if not df_reg.empty:
            # Filtros
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fechas_disponibles = sorted(df_reg['FECHA'].unique()) if 'FECHA' in df_reg.columns else []
                fecha_filtro = st.selectbox("📅 Filtrar por fecha", ["Todas"] + fechas_disponibles)
            
            with col_f2:
                dependencias = sorted(df_reg['DEPENDENCIA'].unique()) if 'DEPENDENCIA' in df_reg.columns else []
                dep_filtro = st.selectbox("🏢 Filtrar por dependencia", ["Todas"] + dependencias)
            
            # Aplicar filtros
            df_filtrado = df_reg.copy()
            if fecha_filtro != "Todas" and 'FECHA' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['FECHA'] == fecha_filtro]
            if dep_filtro != "Todas" and 'DEPENDENCIA' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['DEPENDENCIA'] == dep_filtro]
            
            # Mostrar resultados
            st.write(f"**Resultados:** {len(df_filtrado)} registros")
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
            
            # Exportar reporte
            if not df_filtrado.empty:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 EXPORTAR REPORTE (CSV)",
                    data=csv,
                    file_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("No hay registros para mostrar")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #8b949e; font-size: 12px;'>"
    "Unidad Regional V - Sistema Táctico de Gestión de Personal | © 2024"
    "</p>", 
    unsafe_allow_html=True
)
