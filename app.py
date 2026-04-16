import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Regional V - Diagnóstico", layout="wide")

st.title("🔍 DIAGNÓSTICO - Verificación de nombres")

# --- CONEXIÓN ---
@st.cache_resource
def conectar_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["general"]["spreadsheet_id"])

# --- LEER REGISTROS ---
sheet = conectar_gsheet()
ws_reg = sheet.worksheet("Registros")
data = ws_reg.get_all_values()

df_registros = pd.DataFrame(data[1:], columns=data[0])
df_registros.columns = [c.strip() for c in df_registros.columns]

# --- LEER NÓMINA ---
ws_nom = sheet.worksheet("Nómina")
data_nom = ws_nom.get_all_values()
df_nomina = pd.DataFrame(data_nom[1:], columns=data_nom[0])
df_nomina.columns = [c.strip() for c in df_nomina.columns]

st.success(f"✅ Registros cargados: {len(df_registros)}")
st.success(f"✅ Nómina cargada: {len(df_nomina)}")

# --- MOSTRAR NOMBRES ÚNICOS EN REGISTROS ---
st.subheader("📋 Nombres que existen en la columna 'APELLIDO Y NOMBRES' (Registros):")
nombres_en_registros = df_registros['APELLIDO Y NOMBRES'].dropna().unique()
st.write(f"Total: {len(nombres_en_registros)} nombres")
for nombre in sorted(nombres_en_registros)[:20]:
    st.write(f"• '{nombre}'")

# --- SELECTOR PARA PROBAR ---
st.subheader("🔎 Prueba de comparación:")

# Selector de la nómina
lista_nomina = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
nombre_seleccionado = st.selectbox("Seleccioná un efectivo de la nómina:", lista_nomina)

if nombre_seleccionado:
    st.write(f"**Nombre seleccionado:** '{nombre_seleccionado}'")
    
    # Buscar coincidencia EXACTA
    st.subheader("🔍 Búsqueda EXACTA:")
    exactos = df_registros[df_registros['APELLIDO Y NOMBRES'] == nombre_seleccionado]
    
    if len(exactos) > 0:
        st.error(f"⚠️ ¡ENCONTRADO! El nombre '{nombre_seleccionado}' aparece {len(exactos)} vez/veces:")
        st.dataframe(exactos[['FECHA', 'APELLIDO Y NOMBRES']])
    else:
        st.success(f"✅ No se encontró el nombre exacto '{nombre_seleccionado}'")
        
        # Buscar coincidencias PARCIALES
        st.subheader("🔍 Coincidencias parciales (contiene el texto):")
        parciales = df_registros[df_registros['APELLIDO Y NOMBRES'].str.contains(nombre_seleccionado[:10], case=False, na=False)]
        if len(parciales) > 0:
            st.write("Se encontraron estos nombres similares:")
            for nombre in parciales['APELLIDO Y NOMBRES'].unique():
                st.write(f"• '{nombre}'")
        else:
            st.write("No se encontraron nombres similares")
        
        # Mostrar comparación visual
        st.subheader("📊 Comparación visual:")
        st.write(f"**De la nómina:** '{nombre_seleccionado}'")
        st.write(f"**Longitud:** {len(nombre_seleccionado)} caracteres")
        st.write(f"**Caracteres:** {list(nombre_seleccionado)}")
        
        st.write("**Primeros 5 nombres de registros:**")
        for nombre_reg in df_registros['APELLIDO Y NOMBRES'].head(5):
            st.write(f"• '{nombre_reg}' (longitud: {len(nombre_reg)})")
            if nombre_reg == nombre_seleccionado:
                st.write("  → ¡COINCIDENCIA EXACTA!")

# --- MOSTrar ejemplo con BULACIO ---
st.divider()
st.subheader("🎯 Prueba específica con 'BULACIO':")
bulacios_registros = df_registros[df_registros['APELLIDO Y NOMBRES'].str.contains('BULACIO', case=False, na=False)]
st.write("Nombres encontrados con 'BULACIO' en registros:")
for nombre in bulacios_registros['APELLIDO Y NOMBRES'].unique():
    st.write(f"• '{nombre}'")
    
bulacios_nomina = df_nomina[df_nomina['APELLIDO Y NOMBRES'].str.contains('BULACIO', case=False, na=False)]
st.write("Nombres encontrados con 'BULACIO' en nómina:")
for nombre in bulacios_nomina['APELLIDO Y NOMBRES'].unique():
    st.write(f"• '{nombre}'")
