import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (ESTILO MODERNO) ---
st.set_page_config(
    page_title="Gestión de Servicios Regional",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado para mejorar la estética
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: bold;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_stdio=True)

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

# --- INICIALIZACIÓN DE SESIÓN ---
if 'lista_temporal' not in st.session_state:
    st.session_state.lista_temporal = []
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    col_login, _ = st.columns([1, 2])
    with col_login:
        st.title("🔐 Acceso al Sistema")
        st.subheader("Control Regional de Servicios")
        with st.form("login_form"):
            u = st.text_input("Usuario", placeholder="Ingrese su DNI")
            p = st.text_input("Clave", type="password", placeholder="••••••••")
            if st.form_submit_button("Iniciar Sesión"):
                sheet = conectar_gsheet()
                if sheet:
                    df_users = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                    df_users.columns = [c.strip() for c in df_users.columns]
                    match = df_users[(df_users['Usuario'].astype(str) == u) & (df_users['Clave'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.logueado = True
                        st.rerun()
                    else:
                        st.error("Credenciales no válidas")
else:
    # --- INTERFAZ PRINCIPAL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2562/2562381.png", width=100)
        st.title("Panel de Control")
        st.write("---")
        st.success("Sesión Activa")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"logueado": False, "lista_temporal": []})
            st.rerun()

    st.title("👮‍♂️ Registro Centralizado de Servicios")
    st.write("Carga rápida de efectivos para todas las dependencias.")

    sheet = conectar_gsheet()
    if sheet:
        # Carga de datos
        with st.spinner("Sincronizando con base de datos..."):
            df_nomina = pd.DataFrame(sheet.worksheet("Nómina").get_all_records())
            df_nomina.columns = [c.strip() for c in df_nomina.columns]
            
            data_reg = sheet.worksheet("Registros").get_all_records()
            df_reg = pd.DataFrame(data_reg) if data_reg else pd.DataFrame(columns=['FECHA', 'APELLIDO Y NOMBRES', 'DNI', 'DEPENDENCIA', 'OBSERVACIONES'])
            if not df_reg.empty: df_reg.columns = [c.strip() for c in df_reg.columns]

        # Dashboard de métricas rápidas
        m1, m2, m3 = st.columns(3)
        m1.metric("Pendientes de envío", len(st.session_state.lista_temporal))
        m2.metric("Total Nómina", len(df_nomina))
        m3.metric("Último Registro", df_reg['FECHA'].iloc[-1] if not df_reg.empty else "N/A")

        st.write("---")

        col_input, col_preview = st.columns([1, 1.5], gap="large")

        with col_input:
            st.subheader("➕ Nuevo Registro")
            with st.container():
                fecha_sel = st.date_input("Fecha del Servicio", datetime.now())
                
                nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
                agente_sel = st.selectbox("Buscar por Apellido y Nombre", ["--- Seleccione ---"] + nombres)
                
                obs = st.text_input("Observaciones generales", placeholder="Ej: Recargo 12hs")

                if agente_sel != "--- Seleccione ---":
                    datos = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel].iloc[0]
                    dni = str(datos['DNI'])
                    dep = datos['DEPENDENCIA']
                    
                    # Verificación de historial
                    if 'DNI' in df_reg.columns:
                        previos = df_reg[df_reg['DNI'].astype(str) == dni]
                        if not previos.empty:
                            st.warning(f"⚠️ El efectivo ya registra servicios previos.")
                            with st.expander("Ver historial"):
                                st.write(previos[['FECHA', 'DEPENDENCIA', 'OBSERVACIONES']])

                    if st.button("✨ Añadir a la Lista"):
                        st.session_state.lista_temporal.append({
                            "FECHA": str(fecha_sel),
                            "APELLIDO Y NOMBRES": agente_sel,
                            "DNI": dni,
                            "DEPENDENCIA": dep,
                            "OBSERVACIONES": obs
                        })
                        st.rerun()

        with col_preview:
            st.subheader("📝 Revisión de Carga")
            if st.session_state.lista_temporal:
                df_temp = pd.DataFrame(st.session_state.lista_temporal)
                st.dataframe(df_temp[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA', 'OBSERVACIONES']], 
                             use_container_width=True, hide_index=True)
                
                st.write("")
                c_env, c_vac = st.columns(2)
                with c_env:
                    if st.button("💾 CONFIRMAR Y GUARDAR", type="primary"):
                        with st.spinner("Guardando en la nube..."):
                            pestaña_reg = sheet.worksheet("Registros")
                            for row in st.session_state.lista_temporal:
                                pestaña_reg.append_row(list(row.values()))
                            st.balloons()
                            st.success(f"¡{len(st.session_state.lista_temporal)} servicios guardados correctamente!")
                            st.session_state.lista_temporal = []
                            # st.rerun() se omite aquí para mostrar el mensaje de éxito un momento
                with c_vac:
                    if st.button("🗑️ Limpiar Lista"):
                        st.session_state.lista_temporal = []
                        st.rerun()
            else:
                st.info("No hay datos en la lista de espera actualmente.")
