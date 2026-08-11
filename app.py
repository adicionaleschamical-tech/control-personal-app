import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json
import time
import os

# ============================================================
# 🔍 VERIFICACIÓN DE VERSIÓN - 10/08/2026 23:30
# ============================================================
st.error(f"""
🔴🔴🔴 VERSIÓN DESDE GITHUB 🔴🔴🔴
Fecha: 10/08/2026 23:30
Hash: {os.environ.get('GITHUB_SHA', 'NO GITHUB - LOCAL')}
Archivo: app.py
""")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Regional V - Sistema de Gestión",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VERSIÓN DEL CÓDIGO - VERIFICACIÓN VISIBLE ---
st.markdown("""
    <div style="background: #ff6b6b; color: white; padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; font-weight: bold; font-size: 1.2rem; text-align: center;">
        🚨 VERSIÓN CORREGIDA (25/11/2024) 
        <span style="background: white; color: #ff6b6b; padding: 2px 10px; border-radius: 5px; margin-left: 10px;">VERIFICACIÓN OK</span>
    </div>
""", unsafe_allow_html=True)

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
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- FUNCIONES DE LECTURA ---
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

def leer_usuarios(sheet):
    """Lee la hoja Usuarios y detecta automáticamente los nombres de columnas"""
    try:
        ws_usuarios = sheet.worksheet("Usuarios")
        data = ws_usuarios.get_all_values()
        if len(data) > 1:
            # Limpiar headers: eliminar espacios y convertir a mayúsculas
            headers = []
            for h in data[0]:
                h_clean = str(h).strip().upper()
                headers.append(h_clean)
            
            # Crear DataFrame
            df = pd.DataFrame(data[1:], columns=headers)
            
            # Limpiar valores
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            
            # DEBUG: mostrar qué columnas se encontraron
            st.write("🔍 **DEBUG - Columnas encontradas en Usuarios:**", df.columns.tolist())
            st.write("🔍 **Primeras filas:**")
            st.dataframe(df.head(3))
            
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer Usuarios: {e}")
        return pd.DataFrame()

def guardar_propuesta(sheet, usuario_dni, usuario_nombre, dependencia, datos_originales, datos_nuevos):
    try:
        try:
            ws = sheet.worksheet("Propuestas")
        except:
            ws = sheet.add_worksheet(title="Propuestas", rows=1000, cols=20)
            ws.update([['ID', 'FECHA', 'USUARIO_DNI', 'USUARIO_NOMBRE', 'DEPENDENCIA', 'ACCION', 'DATOS_ORIGINALES', 'DATOS_NUEVOS', 'ESTADO']])
        
        propuestas_data = ws.get_all_values()
        if len(propuestas_data) > 1:
            header = propuestas_data[0]
            prop_data = propuestas_data[1:]
            df_prop = pd.DataFrame(prop_data, columns=header)
        else:
            df_prop = pd.DataFrame(columns=['ID', 'FECHA', 'USUARIO_DNI', 'USUARIO_NOMBRE', 'DEPENDENCIA', 'ACCION', 'DATOS_ORIGINALES', 'DATOS_NUEVOS', 'ESTADO'])
        
        nuevo_id = len(df_prop) + 1 if not df_prop.empty else 1
        fecha_arg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        nueva_fila = [str(nuevo_id), fecha_arg, usuario_dni, usuario_nombre, dependencia, 'MODIFICAR', 
                      json.dumps(datos_originales, ensure_ascii=False), 
                      json.dumps(datos_nuevos, ensure_ascii=False), 'PENDIENTE']
        
        ws.append_row(nueva_fila)
        return True
    except Exception as e:
        st.error(f"Error al guardar propuesta: {e}")
        return False

def aprobar_propuesta(sheet, id_propuesta, admin_dni, admin_nombre):
    try:
        ws = sheet.worksheet("Propuestas")
        propuestas_data = ws.get_all_values()
        if len(propuestas_data) <= 1:
            return False, "No hay propuestas"
        
        header = propuestas_data[0]
        prop_data = propuestas_data[1:]
        df_prop = pd.DataFrame(prop_data, columns=header)
        
        propuesta = df_prop[df_prop['ID'].astype(str) == str(id_propuesta)].iloc[0]
        
        if propuesta['ESTADO'] != 'PENDIENTE':
            return False, "La propuesta ya fue procesada"
        
        datos_nuevos = json.loads(propuesta['DATOS_NUEVOS'])
        datos_originales = json.loads(propuesta['DATOS_ORIGINALES'])
        
        ws_nomina = sheet.worksheet("Nómina")
        nomina_data = ws_nomina.get_all_values()
        header_nomina = nomina_data[0]
        
        dni_modificar = datos_nuevos.get('DNI')
        nombre_modificar = datos_nuevos.get('APELLIDO Y NOMBRES')
        
        cambios_aplicados = []
        fila_encontrada = False
        
        if dni_modificar and 'DNI' in header_nomina:
            col_dni_idx = header_nomina.index('DNI')
            for i, row in enumerate(nomina_data[1:], start=2):
                if len(row) > col_dni_idx and row[col_dni_idx] == str(dni_modificar):
                    for col_idx, col_name in enumerate(header_nomina):
                        if col_name in datos_nuevos:
                            original = datos_originales.get(col_name, '')
                            nuevo = datos_nuevos.get(col_name, '')
                            if str(original) != str(nuevo):
                                ws_nomina.update_cell(i, col_idx+1, str(nuevo))
                                cambios_aplicados.append(f"{col_name}: {original} → {nuevo}")
                    fila_encontrada = True
                    break
        
        if not fila_encontrada and nombre_modificar and 'APELLIDO Y NOMBRES' in header_nomina:
            col_nombre_idx = header_nomina.index('APELLIDO Y NOMBRES')
            for i, row in enumerate(nomina_data[1:], start=2):
                if len(row) > col_nombre_idx and row[col_nombre_idx] == nombre_modificar:
                    for col_idx, col_name in enumerate(header_nomina):
                        if col_name in datos_nuevos:
                            original = datos_originales.get(col_name, '')
                            nuevo = datos_nuevos.get(col_name, '')
                            if str(original) != str(nuevo):
                                ws_nomina.update_cell(i, col_idx+1, str(nuevo))
                                cambios_aplicados.append(f"{col_name}: {original} → {nuevo}")
                    fila_encontrada = True
                    break
        
        registrar_auditoria(sheet, admin_dni, admin_nombre, propuesta['DEPENDENCIA'], 
                          f"APROBACION_CAMBIO: {propuesta['USUARIO_NOMBRE']} propuso - " + "; ".join(cambios_aplicados))
        
        df_prop.loc[df_prop['ID'].astype(str) == str(id_propuesta), 'ESTADO'] = 'APROBADO'
        
        ws.clear()
        ws.update([df_prop.columns.tolist()] + df_prop.values.tolist())
        
        return True, f"Propuesta aprobada. Cambios: {'; '.join(cambios_aplicados)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def rechazar_propuesta(sheet, id_propuesta):
    try:
        ws = sheet.worksheet("Propuestas")
        propuestas_data = ws.get_all_values()
        if len(propuestas_data) <= 1:
            return False, "No hay propuestas"
        
        header = propuestas_data[0]
        prop_data = propuestas_data[1:]
        df_prop = pd.DataFrame(prop_data, columns=header)
        
        df_prop.loc[df_prop['ID'].astype(str) == str(id_propuesta), 'ESTADO'] = 'RECHAZADO'
        
        ws.clear()
        ws.update([df_prop.columns.tolist()] + df_prop.values.tolist())
        
        return True, "Propuesta rechazada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def registrar_auditoria(sheet, usuario_dni, usuario_nombre, dependencia, detalle):
    try:
        try:
            ws = sheet.worksheet("Auditoria")
        except:
            ws = sheet.add_worksheet(title="Auditoria", rows=1000, cols=20)
            ws.update([['ID', 'FECHA', 'USUARIO_DNI', 'USUARIO_NOMBRE', 'DEPENDENCIA', 'ACCION', 'DETALLE']])
        
        auditoria_data = ws.get_all_values()
        if len(auditoria_data) > 1:
            header = auditoria_data[0]
            aud_data = auditoria_data[1:]
            df_aud = pd.DataFrame(aud_data, columns=header)
        else:
            df_aud = pd.DataFrame(columns=['ID', 'FECHA', 'USUARIO_DNI', 'USUARIO_NOMBRE', 'DEPENDENCIA', 'ACCION', 'DETALLE'])
        
        nuevo_id = len(df_aud) + 1 if not df_aud.empty else 1
        fecha_arg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        nueva_fila = [str(nuevo_id), fecha_arg, usuario_dni, usuario_nombre, dependencia, 'PROPUESTA_CAMBIO', detalle]
        ws.append_row(nueva_fila)
        return True
    except Exception as e:
        return False

def cerrar_mes(sheet):
    try:
        ws_registros = sheet.worksheet("Registros")
        data = ws_registros.get_all_values()
        
        if len(data) <= 1:
            return False, "No hay datos para archivar."

        nombre_historico = f"Backup_{datetime.now().strftime('%m_%Y_%H%M')}"
        nueva_ws = sheet.add_worksheet(title=nombre_historico, rows=len(data), cols=len(data[0]))
        nueva_ws.update(data)
        
        headers = [data[0]]
        ws_registros.clear()
        ws_registros.update(headers, 'A1')
        
        return True, f"Mes cerrado. Historial guardado como: {nombre_historico}"
    except Exception as e:
        return False, f"Error al cerrar mes: {str(e)}"

# --- INICIALIZAR SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'confirmar_carga' not in st.session_state:
    st.session_state.confirmar_carga = None
if 'rol_usuario' not in st.session_state:
    st.session_state.rol_usuario = 'COMUN'
if 'fila_seleccionada' not in st.session_state:
    st.session_state.fila_seleccionada = None

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
                    df_u = leer_usuarios(sheet)
                    
                    # Buscar usando nombres normalizados
                    if 'DNI' in df_u.columns and 'CLAVE' in df_u.columns:
                        match = df_u[(df_u['DNI'] == u) & (df_u['CLAVE'] == p)]
                        if not match.empty:
                            st.session_state.logueado = True
                            user = match.iloc[0]
                            st.session_state.user_info = {
                                'dni': u, 
                                'nombre': user.get('NOMBRE', u),
                                'dependencia': user.get('DEPENDENCIA', ''),
                                'jerarquia': user.get('JERARQUÍA', ''),
                                'funcion': user.get('FUNCIÓN', '')
                            }
                            funcion = str(user.get('FUNCIÓN', '')).upper().strip()
                            if 'ADMINISTRADOR' in funcion or 'ADMIN' in funcion:
                                st.session_state.rol_usuario = 'ADMINISTRADOR'
                            elif 'SUPERVISOR' in funcion or 'SUPER' in funcion:
                                st.session_state.rol_usuario = 'SUPERVISOR'
                            else:
                                st.session_state.rol_usuario = 'COMUN'
                            st.rerun()
                        else:
                            st.error("DNI o Clave incorrectos")
                    else:
                        st.error(f"Columnas requeridas no encontradas. Columnas disponibles: {df_u.columns.tolist()}")
                else:
                    st.error("Error de conexión a Google Sheets")
else:
    # --- APP PRINCIPAL ---
    sheet = conectar_gsheet()
    if sheet is None:
        st.stop()
    
    df_nomina = leer_nomina(sheet)
    df_registros = leer_registros(sheet)
    
    es_admin = st.session_state.rol_usuario == 'ADMINISTRADOR'
    es_supervisor = st.session_state.rol_usuario == 'SUPERVISOR'
    es_comun = st.session_state.rol_usuario == 'COMUN'
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2092/2092663.png", width=70)
        st.write(f"**Operador:** {st.session_state.user_info['nombre']}")
        st.write(f"**Rol:** {st.session_state.rol_usuario}")
        st.write(f"**Dependencia:** {st.session_state.user_info.get('dependencia', '')}")
        
        st.divider()
        
        opcion = st.radio("📌 Sección", ["📋 Nómina", "📝 Carga de Servicios", "📊 Propuestas Pendientes"])
        
        st.divider()
        
        if es_admin:
            st.subheader("⚙️ Administración")
            with st.expander("Finalizar Período"):
                st.info("Esta acción moverá los registros a una hoja nueva y vaciará la tabla actual.")
                if st.button("🚀 CERRAR MES", use_container_width=True):
                    exito, msg = cerrar_mes(sheet)
                    if exito:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)
            st.divider()
        
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # --- TÍTULO PRINCIPAL ---
    st.title("👮‍♂️ Sistema de Gestión - UR-V")
    
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.session_state.mensaje_exito = None
    
    # ============================================================
    # SECCIÓN 1: NÓMINA
    # ============================================================
    if opcion == "📋 Nómina":
        st.header("📋 Nómina de Personal")
        
        if df_nomina.empty:
            st.warning("No hay datos en la Nómina")
        else:
            st.info(f"📊 Total de registros: {len(df_nomina)}")
            
            # Mostrar la tabla completa
            st.dataframe(
                df_nomina,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            st.divider()
            
            # --- USUARIO COMÚN: PROPORNER CAMBIOS ---
            if es_comun:
                st.subheader("✏️ Proponer Cambios")
                st.caption("Selecciona un agente para modificar sus datos")
                
                if 'APELLIDO Y NOMBRES' in df_nomina.columns:
                    lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist())
                    agente_seleccionado = st.selectbox("Seleccionar agente:", lista_nombres)
                    
                    if agente_seleccionado:
                        agente_data = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_seleccionado].iloc[0]
                        
                        st.markdown("---")
                        st.subheader(f"📝 Modificar datos de: {agente_seleccionado}")
                        
                        with st.form(key="form_propuesta"):
                            st.markdown("**Complete los campos que desea modificar:**")
                            
                            nuevos_valores = {}
                            columnas_a_mostrar = [col for col in df_nomina.columns if col not in ['N°', 'ID']]
                            
                            cols = st.columns(3)
                            for idx, col in enumerate(columnas_a_mostrar):
                                valor_actual = agente_data[col]
                                with cols[idx % 3]:
                                    label = col
                                    if col.upper() == "ULTIMO ASCENSO":
                                        nuevos_valores[col] = st.text_input(f"📌 {label}", value=str(valor_actual), key=f"edit_{col}")
                                    else:
                                        nuevos_valores[col] = st.text_input(label, value=str(valor_actual), key=f"edit_{col}")
                            
                            st.divider()
                            
                            submitted = st.form_submit_button("📤 ENVIAR PROPUESTA", type="primary", use_container_width=True)
                            
                            if submitted:
                                datos_originales = {}
                                datos_nuevos = {}
                                cambios = []
                                
                                for col, nuevo_valor in nuevos_valores.items():
                                    valor_original = str(agente_data.get(col, ''))
                                    if valor_original != nuevo_valor:
                                        datos_originales[col] = valor_original
                                        datos_nuevos[col] = nuevo_valor
                                        cambios.append(f"{col}: '{valor_original}' → '{nuevo_valor}'")
                                
                                if not cambios:
                                    st.warning("⚠️ No se detectaron cambios. Modifique algún campo antes de enviar.")
                                else:
                                    if guardar_propuesta(
                                        sheet,
                                        st.session_state.user_info['dni'],
                                        st.session_state.user_info['nombre'],
                                        st.session_state.user_info.get('dependencia', ''),
                                        datos_originales,
                                        datos_nuevos
                                    ):
                                        registrar_auditoria(
                                            sheet,
                                            st.session_state.user_info['dni'],
                                            st.session_state.user_info['nombre'],
                                            st.session_state.user_info.get('dependencia', ''),
                                            f"Propuesta de cambios para {agente_seleccionado}: " + "; ".join(cambios)
                                        )
                                        st.success(f"✅ Propuesta enviada correctamente!")
                                        st.info(f"**Cambios propuestos:**\n\n" + "\n".join([f"- {c}" for c in cambios]))
                                        st.balloons()
                                        time.sleep(2)
                                        st.rerun()
                else:
                    st.warning("No se encontró la columna 'APELLIDO Y NOMBRES' en los datos")
            
            elif es_supervisor:
                st.info("🔍 Modo Solo Lectura - No puedes realizar modificaciones")
            
            elif es_admin:
                st.info("✏️ Modo Administrador - Puedes editar directamente")
                
                edited_df = st.data_editor(
                    df_nomina,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_nomina_admin"
                )
                
                if not df_nomina.equals(edited_df):
                    col_guardar, _ = st.columns([1, 4])
                    with col_guardar:
                        if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
                            try:
                                ws_nomina = sheet.worksheet("Nómina")
                                ws_nomina.clear()
                                ws_nomina.update([edited_df.columns.tolist()] + edited_df.values.tolist())
                                st.success("✅ Cambios guardados correctamente")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")
    
    # ============================================================
    # SECCIÓN 2: CARGA DE SERVICIOS
    # ============================================================
    elif opcion == "📝 Carga de Servicios":
        st.header("📝 Carga de Servicios")
        
        if st.session_state.confirmar_carga:
            agente, fecha, fechas_previas = st.session_state.confirmar_carga
            st.warning(f"⚠️ **{agente} YA TIENE {len(fechas_previas)} REGISTRO(S)**")
            st.info("¿Desea cargar otro servicio de todas formas?")
            
            c_si, c_no = st.columns(2)
            with c_si:
                if st.button("✅ SÍ, CARGAR", use_container_width=True):
                    datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente].iloc[0]
                    nuevo_reg = [fecha, agente, str(datos_ag['DNI']), datos_ag['DEPENDENCIA'], "CARGA EXTRA"]
                    sheet.worksheet("Registros").append_row(nuevo_reg)
                    st.session_state.confirmar_carga = None
                    st.session_state.mensaje_exito = f"✅ Servicio guardado para {agente}"
                    st.rerun()
            with c_no:
                if st.button("❌ CANCELAR", use_container_width=True):
                    st.session_state.confirmar_carga = None
                    st.rerun()
            st.stop()

        c1, c2, c3 = st.columns(3)
        c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
        c2.metric("📝 TOTAL CARGAS", len(df_registros))
        c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))
        
        st.divider()
        
        col_form, col_list = st.columns([1, 1.3], gap="large")
        
        with col_form:
            st.subheader("📝 Nuevo Registro")
            with st.form("registro_form", clear_on_submit=True):
                f_input = st.date_input("Fecha", datetime.now())
                lista_nombres = sorted(df_nomina['APELLIDO Y NOMBRES'].tolist()) if not df_nomina.empty else []
                agente_sel = st.selectbox("Efectivo", ["-- SELECCIONE --"] + lista_nombres)
                
                submitted = st.form_submit_button("💾 GUARDAR SERVICIO", type="primary", use_container_width=True)
                
                if submitted:
                    if agente_sel == "-- SELECCIONE --":
                        st.warning("Seleccione un agente")
                    else:
                        existe = (df_registros['APELLIDO Y NOMBRES'] == agente_sel).any() if not df_registros.empty else False
                        if existe:
                            previas = df_registros[df_registros['APELLIDO Y NOMBRES'] == agente_sel]['FECHA'].tolist()
                            st.session_state.confirmar_carga = (agente_sel, f_input.strftime("%d/%m/%Y"), previas)
                            st.rerun()
                        else:
                            datos_ag = df_nomina[df_nomina['APELLIDO Y NOMBRES'] == agente_sel].iloc[0]
                            nuevo_reg = [f_input.strftime("%d/%m/%Y"), agente_sel, str(datos_ag['DNI']), datos_ag['DEPENDENCIA'], ""]
                            sheet.worksheet("Registros").append_row(nuevo_reg)
                            st.session_state.mensaje_exito = f"✅ Servicio de {agente_sel} guardado!"
                            st.rerun()
        
        with col_list:
            st.subheader("📋 Últimos Servicios")
            if not df_registros.empty:
                st.dataframe(df_registros.tail(10), use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros recientes.")
    
    # ============================================================
    # SECCIÓN 3: PROPUESTAS PENDIENTES
    # ============================================================
    elif opcion == "📊 Propuestas Pendientes":
        st.header("📊 Propuestas de Cambio")
        
        if not es_admin:
            st.warning("⚠️ Solo los Administradores pueden ver y gestionar propuestas.")
        else:
            try:
                try:
                    ws_prop = sheet.worksheet("Propuestas")
                except:
                    st.info("No hay propuestas pendientes")
                    st.stop()
                
                prop_data = ws_prop.get_all_values()
                if len(prop_data) <= 1:
                    st.info("No hay propuestas pendientes")
                else:
                    header = prop_data[0]
                    data = prop_data[1:]
                    df_prop = pd.DataFrame(data, columns=header)
                    
                    df_pendientes = df_prop[df_prop['ESTADO'] == 'PENDIENTE']
                    
                    if df_pendientes.empty:
                        st.info("✅ No hay propuestas pendientes de revisión")
                    else:
                        st.info(f"📌 {len(df_pendientes)} propuestas pendientes de revisión")
                        
                        for idx, prop in df_pendientes.iterrows():
                            with st.container():
                                st.markdown(f"### 📋 Propuesta #{prop['ID']}")
                                st.markdown(f"**Fecha:** {prop['FECHA']}")
                                st.markdown(f"**Usuario:** {prop['USUARIO_NOMBRE']} (DNI: {prop['USUARIO_DNI']})")
                                st.markdown(f"**Dependencia:** {prop['DEPENDENCIA']}")
                                
                                try:
                                    datos_originales = json.loads(prop['DATOS_ORIGINALES'])
                                    datos_nuevos = json.loads(prop['DATOS_NUEVOS'])
                                    
                                    st.markdown("**Cambios propuestos:**")
                                    cambios_df = pd.DataFrame({
                                        'Campo': list(datos_originales.keys()),
                                        'Valor actual': list(datos_originales.values()),
                                        'Valor propuesto': list(datos_nuevos.values())
                                    })
                                    st.dataframe(cambios_df, use_container_width=True, hide_index=True)
                                except:
                                    st.write("Datos originales:", prop['DATOS_ORIGINALES'])
                                    st.write("Datos nuevos:", prop['DATOS_NUEVOS'])
                                
                                col_a, col_r = st.columns(2)
                                with col_a:
                                    if st.button(f"✅ Aprobar #{prop['ID']}", key=f"aprobar_{prop['ID']}", use_container_width=True):
                                        exito, msg = aprobar_propuesta(
                                            sheet, 
                                            prop['ID'], 
                                            st.session_state.user_info['dni'],
                                            st.session_state.user_info['nombre']
                                        )
                                        if exito:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                
                                with col_r:
                                    if st.button(f"❌ Rechazar #{prop['ID']}", key=f"rechazar_{prop['ID']}", use_container_width=True):
                                        exito, msg = rechazar_propuesta(sheet, prop['ID'])
                                        if exito:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                
                                st.divider()
            except Exception as e:
                st.info("ℹ️ No hay hoja de propuestas aún. Se creará automáticamente cuando se envíe la primera.")
