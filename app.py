import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Servicios", layout="wide")

# Función de conexión con manejo de errores visible
def conectar_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        if "gcp_service_account" not in st.secrets:
            st.error("No se encontró la configuración 'gcp_service_account' en los Secrets.")
            return None
        
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["general"]["spreadsheet_id"])
    except Exception as e:
        st.error(f"Error detallado de conexión: {e}")
        return None

# Intentar una conexión inicial para despertar la app
sheet = conectar_gsheet()
if sheet:
    st.success("Conexión con Google Sheets establecida correctamente.")
else:
    st.warning("Esperando configuración correcta de los Secrets...")
