import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Regional V - Carga", layout="wide")

st.title("👮‍♂️ Carga de Servicios - UR-V")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["general"]["spreadsheet_id"])

# --- FUNCIÓN PARA LEER REGISTROS SIEMPRE FRESCOS ---
def leer_registros(sheet):
    """Lee los registros DIRECTAMENTE desde Google Sheets"""
    ws_registros = sheet.worksheet("Registros")
    data_registros = ws_registros.get_all_values()
    if len(data_registros) > 1:
        df = pd.DataFrame(data_registros[1:], columns=data_registros[0])
        df.columns = [c.strip() for c in df.columns]
        return df
    return pd.DataFrame()

# --- FUNCIÓN PARA LEER NÓMINA ---
def leer_nomina(sheet):
    """Lee la nómina desde Google Sheets"""
    ws_nomina = sheet.worksheet("Nómina")
    data_nomina = ws_nomina.get_all_values()
    if len(data_nomina) > 1:
        df = pd.DataFrame(data_nomina[1:], columns=data_nomina[0])
        df.columns = [c.strip() for c in df.columns]
        return df
    return pd.DataFrame()

# --- OBTENER CONEXIÓN ---
sheet = conectar_gsheet()

# --- LEER DATOS FRESCOS CADA VEZ ---
df_nomina = leer_nomina(sheet)
df_registros = leer_registros(sheet)

# --- SESIÓN PARA CONTROL ---
if 'recargar' not in st.session_state:
    st.session_state.recargar = False

if st.session_state.recargar:
    st.session_state.recargar = False
    st.rerun()

# --- Mostrar métricas ---
c1, c2, c3 = st.columns(3)
c1.metric("👥 PERSONAL", len(df_nomina))
c2.metric("📝 REGISTROS", len(df_registros))
c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))

st.divider()

# --- MOSTRAR NOMBRES EN REGISTROS (PARA DEPURAR) ---
with st.expander("🔍 Nombres actuales en la columna B (Registros)"):
    if not df_registros.empty:
        nombres_unicos = sorted(df_registros['APELLIDO Y NOMBRES'].unique())
        st.write(f"**Total: {len(nombres_unicos)} nombres únicos**")
        for nombre in nombres_unicos[:30]:
            st.write(f"• {nombre}")
    else:
        st.write("No hay registros")

st.divider()

# --- FORMULARIO ---
col_form, col_list = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 Nuevo Registro")
    
    with st.form("registro_form", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.now())
        lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
        agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
        
        # --- VERIFICACIÓN EN TIEMPO REAL ---
        if agente != "-- SELECCIONE --" and not df_registros.empty:
            # Buscar si el nombre existe EXACTAMENTE
            existe = (df_registros['APELLIDO Y NOMBRES'] == agente).any()
            
            if existe:
                fechas = df_registros[df_registros['APELLIDO Y NOMBRES'] == agente]['FECHA'].tolist()
                st.error(f"⚠️ **ESTE EFECTIVO YA EXISTE EN REGISTROS**")
                st.write(f"Aparece en {len(fechas)} ocasión/es:")
                for f in fechas:
                    st.write(f"  • {f}")
            else:
                st.success("✅ Este efectivo NO tiene registros previos")
        
        submitted = st.form_submit_button("💾 GUARDAR", type="primary", use_container_width=True)
        
        if submitted:
            if agente == "-- SELECCIONE --":
                st.warning("Seleccione un agente")
            else:
                # --- VERIFICAR NUEVAMENTE CON DATOS ACTUALIZADOS ---
                # Recargar registros para asegurar datos frescos
                df_registros_fresco = leer_registros(sheet)
                existe = (df_registros_fresco['APELLIDO Y NOMBRES'] == agente).any()
                
                if existe:
                    st.error(f"❌ NO SE PUEDE GUARDAR: {agente} ya existe en los registros históricos")
                    st.info("Cada efectivo solo puede tener UN servicio en todo el sistema")
                else:
                    # Guardar el nuevo registro
                    datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                    nuevo_reg = [
                        fecha.strftime("%d/%m/%Y"),
                        agente,
                        str(datos_ag['DNI']),
                        datos_ag['DEPENDENCIA'],
                        ""
                    ]
                    
                    try:
                        ws_registros = sheet.worksheet("Registros")
                        ws_registros.append_row(nuevo_reg)
                        st.success(f"✅ ¡Servicio de {agente} guardado!")
                        st.balloons()
                        # Forzar recarga de la página para actualizar todo
                        st.session_state.recargar = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

with col_list:
    st.subheader("📋 Últimos Servicios")
    if not df_registros.empty:
        df_ultimos = df_registros.sort_values('FECHA', ascending=False).head(10)
        st.dataframe(df_ultimos[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']], use_container_width=True, hide_index=True)
        
        # Mostrar estadística
        st.caption(f"Total en sistema: {len(df_registros)} registros")

st.caption("✅ **Sistema actualizado:** Verifica contra Google Sheets en tiempo real")
