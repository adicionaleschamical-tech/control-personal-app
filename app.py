import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (ESTILO PROFESIONAL) ---
st.set_page_config(
    page_title="Sistema Regional de Servicios",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO VISUAL PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    /* Fondo y tipografía general */
    .main {
        background-color: #f0f2f6;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Tarjetas de Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 32px;
        color: #003366;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }

    /* Botones Modernos */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    
    /* Botón Primario (Guardar) */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #003366;
        border: none;
    }

    /* Contenedores de entrada */
    .stSelectbox, .stDateInput, .stTextInput {
        margin-bottom: 15px;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #002244;
        font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def conectar_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None

# --- MANEJO DE ESTADO DE SESIÓN ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

# --- PANTALLA DE ACCESO (LOGIN) ---
if not st.session_state.logueado:
    _, col_center, _ = st.columns([1, 1.2, 1])
    with col_center:
        st.write("")
        st.write("")
        st.title("🔐 Acceso Restringido")
        st.info("Ingrese sus credenciales para gestionar los servicios regionales.")
        with st.form("login_form"):
            u = st.text_input("Usuario (DNI)")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("INGRESAR AL SISTEMA"):
                sheet = conectar_gsheet()
                if sheet:
                    df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                    df_users.columns = [c.strip() for c in df_users.columns]
                    match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.logueado = True
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Verifique e intente nuevamente.")
else:
    # --- INTERFAZ DE ADMINISTRADOR ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1022/1022334.png", width=80)
        st.title("Gestión UR-V")
        st.write("---")
        st.success(f"Sesión Activa")
        if st.button("CERRAR SESIÓN"):
            st.session_state.update({"logueado": False, "lista_temporal": []})
            st.rerun()

    st.title("👮‍♂️ Carga Central de Servicios Regionales")
    
    sheet = conectar_gsheet()
    if sheet:
        # Carga silenciosa de datos
        with st.spinner("Sincronizando con la nube..."):
            df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
            df_nomina.columns = [c.strip() for c in df_nomina.columns]
            
            data_reg = sheet.worksheet("Registros").get_all_records()
            df_reg = pd.DataFrame(data_reg) if data_reg else pd.DataFrame(columns=['FECHA', 'APELLIDO Y NOMBRES', 'DNI', 'DEPENDENCIA', 'OBSERVACIONES'])
            if not df_reg.empty: df_reg.columns = [c.strip() for c in df_reg.columns]

        # Dashboard de métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("📦 En espera de envío", len(st.session_state.lista_temporal))
        m2.metric("👥 Personal en Nómina", len(df_nomina))
        m3.metric("📅 Fecha Hoy", datetime.now().strftime("%d/%m/%Y"))

        st.write("---")

        # Layout Principal
        col_carga, col_vista = st.columns([1, 1.4], gap="large")

        with col_carga:
            st.subheader("📝 Nuevo Registro")
            
            # Selector de Fecha (Calendario con formato DD/MM/AAAA al guardar)
            fecha_raw = st.date_input("Fecha del Servicio", datetime.now())
            fecha_formato = fecha_raw.strftime("%d/%m/%Y")
            
            # Buscador de Personal
            lista_personal = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
            agente = st.selectbox("Buscar Efectivo (Escriba el apellido)", ["--- Seleccione un agente ---"] + lista_personal)
            
            obs_text = st.text_input("Observaciones / Detalles del Servicio")

            if agente != "--- Seleccione un agente ---":
                datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                dni_ag = str(datos_ag['DNI'])
                dep_ag = datos_ag['DEPENDENCIA']
                
                # VALIDACIÓN DE DUPLICADOS (Búsqueda en historial por DNI)
                if 'DNI' in df_reg.columns:
                    previos = df_reg[df_reg['DNI'].astype(str) == dni_ag]
                    if not previos.empty:
                        st.warning(f"⚠️ **REGISTRO EXISTENTE:** {agente} ya figura en el historial.")
                        with st.expander("Ver detalle de fechas anteriores"):
                            st.dataframe(previos[['FECHA', 'DEPENDENCIA', 'OBSERVACIONES']], hide_index=True)

                if st.button("➕ AÑADIR A LA LISTA"):
                    st.session_state.lista_temporal.append({
                        "FECHA": fecha_formato,
                        "APELLIDO Y NOMBRES": agente,
                        "DNI": dni_ag,
                        "DEPENDENCIA": dep_ag,
                        "OBSERVACIONES": obs_text
                    })
                    st.rerun()

        with col_vista:
            st.subheader("📋 Revisión de Carga Actual")
            if st.session_state.lista_temporal:
                df_prev = pd.DataFrame(st.session_state.lista_temporal)
                st.dataframe(
                    df_prev[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA', 'OBSERVACIONES']], 
                    use_container_width=True, 
                    hide_index=True
                )
                
                st.write("")
                btn_env, btn_bor = st.columns(2)
                with btn_env:
                    if st.button("🚀 CONFIRMAR Y GUARDAR TODO", type="primary"):
                        with st.spinner("Impactando datos en el Sheet..."):
                            ws_reg = sheet.worksheet("Registros")
                            for item in st.session_state.lista_temporal:
                                ws_reg.append_row(list(item.values()))
                            
                            st.balloons()
                            st.success(f"Éxito: {len(st.session_state.lista_temporal)} servicios registrados.")
                            st.session_state.lista_temporal = []
                            # st.rerun() omitido para permitir lectura del mensaje de éxito
                with btn_bor:
                    if st.button("🗑️ VACIAR LISTA"):
                        st.session_state.lista_temporal = []
                        st.rerun()
            else:
                st.info("No hay registros pendientes en la lista de carga.")
