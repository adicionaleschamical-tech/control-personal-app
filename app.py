import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="DIAGNÓSTICO - Regional V",
    page_icon="🔧",
    layout="wide"
)

# --- CONEXIÓN ---
@st.cache_resource(ttl=600)
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

# --- LECTURA DIRECTA SIN CACHÉ ---
def leer_registros_directo():
    """Lee la pestaña Registros directamente y muestra diagnóstico"""
    try:
        sheet = conectar_gsheet()
        if not sheet:
            return None
        
        ws = sheet.worksheet("Registros")
        
        # Leer todos los valores
        todos_los_valores = ws.get_all_values()
        
        st.subheader("🔍 DIAGNÓSTICO COMPLETO")
        
        # Mostrar primeras filas
        st.write("**Primeras 5 filas de la hoja 'Registros' (incluyendo encabezado):**")
        for i, fila in enumerate(todos_los_valores[:5]):
            st.write(f"Fila {i}: {fila}")
        
        # Verificar si hay datos
        if len(todos_los_valores) > 1:
            df = pd.DataFrame(todos_los_valores[1:], columns=todos_los_valores[0])
            df.columns = [c.strip() for c in df.columns]
            
            st.success(f"✅ Se cargaron {len(df)} registros")
            
            # Mostrar columnas
            st.write(f"**Columnas encontradas:** {list(df.columns)}")
            
            # Buscar específicamente a BULACIO
            if 'APELLIDO Y NOMBRES' in df.columns:
                df['APELLIDO Y NOMBRES'] = df['APELLIDO Y NOMBRES'].astype(str).str.strip()
                bulacios = df[df['APELLIDO Y NOMBRES'].str.contains('BULACIO', case=False, na=False)]
                
                st.subheader("🎯 Búsqueda de 'BULACIO' en la columna 'APELLIDO Y NOMBRES':")
                if not bulacios.empty:
                    st.write(f"**Encontrados {len(bulacios)} registros:**")
                    st.dataframe(bulacios)
                else:
                    st.error("❌ NO se encontró ningún registro con 'BULACIO'")
                    st.write("Primeros 10 nombres únicos en la columna:")
                    st.write(df['APELLIDO Y NOMBRES'].head(10).tolist())
            
            return df
        else:
            st.warning("La hoja 'Registros' está vacía")
            return None
            
    except Exception as e:
        st.error(f"Error al leer: {e}")
        return None

# --- APP PRINCIPAL ---
st.title("🔧 DIAGNÓSTICO - Conexión con Google Sheets")
st.warning("Esta es una versión de diagnóstico. NO permite guardar registros.")

# Botón para forzar lectura
if st.button("🔍 LEER HOJA 'REGISTROS' AHORA"):
    with st.spinner("Leyendo datos..."):
        df = leer_registros_directo()
        
        if df is not None:
            st.divider()
            st.subheader("📊 Estadísticas")
            st.metric("Total registros", len(df))
            
            # Mostrar los últimos 10 registros
            st.subheader("Últimos 10 registros (orden original):")
            st.dataframe(df.tail(10))

st.info("Si NO ves a BULACIO en la búsqueda, el problema es que la hoja 'Registros' no tiene la columna 'APELLIDO Y NOMBRES' exactamente como está escrita, o los datos no se están sincronizando.")
