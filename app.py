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

# --- LEER DATOS DIRECTAMENTE (SIN NINGÚN CACHÉ COMPLICADO) ---
sheet = conectar_gsheet()

# Leer Nómina
ws_nomina = sheet.worksheet("Nómina")
data_nomina = ws_nomina.get_all_values()
df_nomina = pd.DataFrame(data_nomina[1:], columns=data_nomina[0])
df_nomina.columns = [c.strip() for c in df_nomina.columns]

# Leer Registros
ws_registros = sheet.worksheet("Registros")
data_registros = ws_registros.get_all_values()
df_registros = pd.DataFrame(data_registros[1:], columns=data_registros[0])
df_registros.columns = [c.strip() for c in df_registros.columns]

# Mostrar métricas
c1, c2, c3 = st.columns(3)
c1.metric("👥 PERSONAL", len(df_nomina))
c2.metric("📝 REGISTROS", len(df_registros))
c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))

st.divider()

# --- MOSTRAR LOS NOMBRES QUE EXISTEN EN REGISTROS (PARA VERIFICAR) ---
with st.expander("🔍 Ver nombres existentes en la columna B (Registros)"):
    nombres_registros = df_registros['APELLIDO Y NOMBRES'].tolist()
    st.write(f"**Total: {len(nombres_registros)} nombres**")
    for nombre in sorted(set(nombres_registros))[:20]:
        st.write(f"• {nombre}")

# --- FORMULARIO ---
col_form, col_list = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 Nuevo Registro")
    
    with st.form("registro_form", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.now())
        lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
        agente = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
        
        # --- VERIFICACIÓN EN EL MOMENTO ---
        if agente != "-- SELECCIONE --":
            # Buscar si el nombre existe en la columna B de registros
            existe = agente in df_registros['APELLIDO Y NOMBRES'].values
            
            if existe:
                # Obtener las fechas donde aparece
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
                # Verificar nuevamente antes de guardar
                existe = agente in df_registros['APELLIDO Y NOMBRES'].values
                
                if existe:
                    st.error(f"❌ NO SE PUEDE GUARDAR: {agente} ya existe en los registros históricos")
                    st.info("Cada efectivo solo puede tener UN servicio en todo el sistema")
                else:
                    # Guardar
                    datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                    nuevo_reg = [
                        fecha.strftime("%d/%m/%Y"),
                        agente,
                        str(datos_ag['DNI']),
                        datos_ag['DEPENDENCIA'],
                        ""
                    ]
                    
                    try:
                        ws_registros.append_row(nuevo_reg)
                        st.success(f"✅ ¡Servicio de {agente} guardado!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

with col_list:
    st.subheader("📋 Últimos Servicios")
    if not df_registros.empty:
        df_ultimos = df_registros.sort_values('FECHA', ascending=False).head(10)
        st.dataframe(df_ultimos[['FECHA', 'APELLIDO Y NOMBRES', 'DEPENDENCIA']], use_container_width=True, hide_index=True)

st.caption("✅ Verifica si el efectivo ya existe en la columna B de Registros")
