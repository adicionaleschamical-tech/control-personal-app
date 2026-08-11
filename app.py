import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Regional V - Sistema de Gestión",
    page_icon="👮‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetricValue"] { color: #58a6ff; font-weight: bold; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .ficha-container {
        background: white;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #eef2f7;
        margin: 15px 0;
    }
    .ficha-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
        margin-top: 15px;
    }
    .ficha-item {
        background: #f8fafc;
        padding: 10px 14px;
        border-radius: 10px;
        border: 1px solid #eef2f7;
    }
    .ficha-item-label {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #000000;
        margin-bottom: 2px;
    }
    .ficha-item-valor {
        font-size: 0.95rem;
        font-weight: 500;
        color: #000000;
    }
    .ficha-item-valor.vacio {
        color: #000000;
        font-style: italic;
    }
    .ficha-item.ultimo-ascenso .ficha-item-valor {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #000000 !important;
    }
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
    try:
        ws_usuarios = sheet.worksheet("Usuarios")
        data = ws_usuarios.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def guardar_propuesta(sheet, usuario_dni, usuario_nombre, dependencia, datos_originales, datos_nuevos):
    try:
        ws = sheet.worksheet("Propuestas")
        propuestas_data = ws.get_all_values()
        if len(propuestas_data) > 1:
            header = propuestas_data[0]
            prop_data = propuestas_data[1:]
            df_prop = pd.DataFrame(prop_data, columns=header)
        else:
            df_prop = pd.DataFrame(columns=['ID', 'FECHA', 'USUARIO_DNI', 'USUARIO_NOMBRE', 'DEPENDENCIA', 'ACCION', 'DATOS_ORIGINALES', 'DATOS_NUEVOS', 'ESTADO'])
        
        nuevo_id = len(df_prop) + 1 if not df_prop.empty else 1
        fecha_arg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        nueva_fila = [nuevo_id, fecha_arg, usuario_dni, usuario_nombre, dependencia, 'MODIFICAR', 
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
            return False
        
        header = propuestas_data[0]
        prop_data = propuestas_data[1:]
        df_prop = pd.DataFrame(prop_data, columns=header)
        
        propuesta = df_prop[df_prop['ID'].astype(str) == str(id_propuesta)].iloc[0]
        
        if propuesta['ESTADO'] != 'PENDIENTE':
            return False, "La propuesta ya fue procesada"
        
        datos_nuevos = json.loads(propuesta['DATOS_NUEVOS'])
        datos_originales = json.loads(propuesta['DATOS_ORIGINALES'])
        
        # Aplicar cambios a Nómina
        ws_nomina = sheet.worksheet("Nómina")
        nomina_data = ws_nomina.get_all_values()
        header_nomina = nomina_data[0]
        
        # Buscar el agente por DNI o APELLIDO Y NOMBRES
        dni_modificar = datos_nuevos.get('DNI')
        nombre_modificar = datos_nuevos.get('APELLIDO Y NOMBRES')
        
        cambios_aplicados = []
        if dni_modificar:
            col_dni_idx = header_nomina.index('DNI') if 'DNI' in header_nomina else None
            if col_dni_idx is not None:
                for i, row in enumerate(nomina_data[1:], start=2):
                    if len(row) > col_dni_idx and row[col_dni_idx] == str(dni_modificar):
                        for col_idx, col_name in enumerate(header_nomina):
                            if col_name in datos_nuevos:
                                original = datos_originales.get(col_name, '')
                                nuevo = datos_nuevos.get(col_name, '')
                                if str(original) != str(nuevo):
                                    ws_nomina.update_cell(i, col_idx+1, str(nuevo))
                                    cambios_aplicados.append(f"{col_name}: {original} → {nuevo}")
                        break
        
        # Registrar en auditoría
        registrar_auditoria(sheet, admin_dni, admin_nombre, propuesta['DEPENDENCIA'], 
                          f"APROBACION_CAMBIO: {propuesta['USUARIO_NOMBRE']} propuso - " + "; ".join(cambios_aplicados))
        
        # Actualizar estado de la propuesta
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
            return False
        
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
        ws = sheet.worksheet("Auditoria")
        auditoria_data = ws.get_all_values()
        if len(auditoria_data) > 1:
            header = auditoria_data[0]
            aud_data = auditoria_data[1:]
            df_aud = pd.DataFrame(aud_data, columns=header)
        else:
            df_aud = pd.DataFrame(columns=['ID', 'FECHA', 'USUARIO_DNI', 'USUARIO_NOMBRE', 'DEPENDENCIA', 'ACCION', 'DETALLE'])
        
        nuevo_id = len(df_aud) + 1 if not df_aud.empty else 1
        fecha_arg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        nueva_fila = [nuevo_id, fecha_arg, usuario_dni, usuario_nombre, dependencia, 'PROPUESTA_CAMBIO', detalle]
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
                    match = df_u[(df_u['DNI'].astype(str) == u) & (df_u['CLAVE'].astype(str) == p)]
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
                        # Determinar rol: FUNCIÓN = ADMINISTRADOR, SUPERVISOR, o COMÚN
                        funcion = str(user.get('FUNCIÓN', '')).upper()
                        if 'ADMINISTRADOR' in funcion:
                            st.session_state.rol_usuario = 'ADMINISTRADOR'
                        elif 'SUPERVISOR' in funcion:
                            st.session_state.rol_usuario = 'SUPERVISOR'
                        else:
                            st.session_state.rol_usuario = 'COMUN'
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
else:
    # --- APP PRINCIPAL ---
    sheet = conectar_gsheet()
    if sheet is None:
        st.stop()
    
    df_nomina = leer_nomina(sheet)
    df_registros = leer_registros(sheet)
    df_usuarios = leer_usuarios(sheet)
    
    # Determinar rol
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
        
        # --- NAVEGACIÓN ---
        opcion = st.radio("📌 Sección", ["📋 Nómina", "📝 Carga de Servicios", "📊 Propuestas Pendientes"])
        
        st.divider()
        
        # Herramientas de Administrador
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
    
    st.title("👮‍♂️ Sistema de Gestión - UR-V")
    
    # Mensaje de éxito
    if st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.session_state.mensaje_exito = None
    
    # ============================================================
    # SECCIÓN 1: NÓMINA (TABLA TIPO EXCEL)
    # ============================================================
    if opcion == "📋 Nómina":
        st.header("📋 Nómina de Personal")
        
        if df_nomina.empty:
            st.warning("No hay datos en la Nómina")
        else:
            # --- FILTROS ---
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                dependencias = ["Todas"] + sorted(df_nomina['DEPENDENCIA'].unique().tolist())
                dep_filter = st.selectbox("🏢 Dependencia", dependencias)
            with col_f2:
                jerarquias = ["Todas"] + sorted(df_nomina['JERARQUÍA'].unique().tolist())
                jer_filter = st.selectbox("⭐ Jerarquía", jerarquias)
            with col_f3:
                busqueda = st.text_input("🔍 Buscar", placeholder="Nombre o DNI...")
            
            # --- APLICAR FILTROS ---
            df_filtrado = df_nomina.copy()
            if dep_filter != "Todas":
                df_filtrado = df_filtrado[df_filtrado['DEPENDENCIA'] == dep_filter]
            if jer_filter != "Todas":
                df_filtrado = df_filtrado[df_filtrado['JERARQUÍA'] == jer_filter]
            if busqueda:
                mascara = df_filtrado.astype(str).apply(lambda row: row.str.contains(busqueda, case=False).any(), axis=1)
                df_filtrado = df_filtrado[mascara]
            
            st.caption(f"📊 Mostrando {len(df_filtrado)} de {len(df_nomina)} registros")
            
            # --- MOSTRAR TABLA ---
            # Determinar si el usuario puede editar
            puede_editar = es_admin
            
            if puede_editar:
                st.info("✏️ Modo Edición: Los cambios se aplican directamente")
                # Para administradores: edición directa
                edited_df = st.data_editor(
                    df_filtrado,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_nomina"
                )
                
                # Detectar cambios y guardar
                if not df_filtrado.equals(edited_df):
                    if st.button("💾 GUARDAR CAMBIOS", type="primary"):
                        try:
                            ws_nomina = sheet.worksheet("Nómina")
                            # Actualizar toda la hoja
                            ws_nomina.clear()
                            ws_nomina.update([edited_df.columns.tolist()] + edited_df.values.tolist())
                            st.success("✅ Cambios guardados correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
            else:
                # Para usuarios comunes y supervisores: solo lectura o propuesta
                if es_comun:
                    st.info("📝 Selecciona una fila para proponer cambios")
                    st.caption("Los cambios serán enviados a aprobación del Administrador")
                
                # Mostrar tabla con selección
                event = st.dataframe(
                    df_filtrado,
                    use_container_width=True,
                    hide_index=True,
                    selection_mode="single-row",
                    on_select="rerun"
                )
                
                # Verificar si se seleccionó una fila
                if event and event.selection and "rows" in event.selection and len(event.selection["rows"]) > 0:
                    row_idx = event.selection["rows"][0]
                    if row_idx is not None:
                        idx_original = df_filtrado.index[row_idx]
                        agente = df_filtrado.loc[idx_original]
                        
                        st.markdown("---")
                        st.subheader("📝 Proponer Cambios")
                        
                        # Mostrar ficha del agente con campos editables
                        st.markdown(f"""
                        <div class="ficha-container">
                            <div class="ficha-grid">
                        """, unsafe_allow_html=True)
                        
                        # Crear formulario de edición
                        agente_dict = agente.to_dict()
                        nuevos_valores = {}
                        campos_header = ['APELLIDO Y NOMBRES', 'JERARQUÍA', 'FUNCIÓN', 'DEPENDENCIA']
                        
                        # Usar columnas para organizar los campos
                        cols = st.columns(3)
                        col_idx = 0
                        
                        for col, valor in agente_dict.items():
                            # Saltar campos que no deben editarse
                            if col in ['N°']:
                                continue
                            
                            # Determinar si es ULTIMO ASCENSO para destacarlo
                            es_ultimo_ascenso = col.upper() == "ULTIMO ASCENSO"
                            label = col
                            
                            # Crear campo editable
                            with cols[col_idx % 3]:
                                if col in campos_header:
                                    # Estos campos ya se ven en la ficha, los mostramos como texto
                                    st.markdown(f"**{label}:** {valor}")
                                else:
                                    if es_ultimo_ascenso:
                                        nuevos_valores[col] = st.text_input(f"📌 {label}", value=str(valor), key=f"prop_{col}")
                                    else:
                                        nuevos_valores[col] = st.text_input(label, value=str(valor), key=f"prop_{col}")
                            col_idx += 1
                        
                        st.markdown("</div></div>", unsafe_allow_html=True)
                        
                        # Botón para enviar propuesta
                        col_b1, col_b2 = st.columns([1, 3])
                        with col_b1:
                            if st.button("📤 ENVIAR PROPUESTA", type="primary", use_container_width=True):
                                # Verificar qué campos cambiaron
                                datos_originales = {}
                                datos_nuevos = {}
                                cambios = []
                                for col, nuevo_valor in nuevos_valores.items():
                                    valor_original = str(agente_dict.get(col, ''))
                                    if valor_original != nuevo_valor:
                                        datos_originales[col] = valor_original
                                        datos_nuevos[col] = nuevo_valor
                                        cambios.append(f"{col}: {valor_original} → {nuevo_valor}")
                                
                                if not cambios:
                                    st.warning("No se detectaron cambios")
                                else:
                                    # Guardar propuesta
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
                                            f"Propuesta de cambios para {agente_dict.get('APELLIDO Y NOMBRES', '')}: " + "; ".join(cambios)
                                        )
                                        st.success(f"✅ Propuesta enviada. Cambios: {'; '.join(cambios)}")
                                        st.balloons()
                                        st.rerun()
    
    # ============================================================
    # SECCIÓN 2: CARGA DE SERVICIOS
    # ============================================================
    elif opcion == "📝 Carga de Servicios":
        st.header("📝 Carga de Servicios")
        
        # --- MODAL DE CONFIRMACIÓN DE DUPLICADO ---
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

        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("👥 TOTAL PERSONAL", len(df_nomina))
        c2.metric("📝 TOTAL CARGAS", len(df_registros))
        c3.metric("📅 FECHA", datetime.now().strftime("%d/%m/%Y"))
        
        st.divider()
        
        # --- FORMULARIO ---
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
    # SECCIÓN 3: PROPUESTAS PENDIENTES (SOLO ADMIN)
    # ============================================================
    elif opcion == "📊 Propuestas Pendientes":
        st.header("📊 Propuestas de Cambio")
        
        if not es_admin:
            st.warning("⚠️ Solo los Administradores pueden ver y gestionar propuestas.")
            st.info("Los usuarios comunes pueden proponer cambios desde la sección 'Nómina'.")
        else:
            try:
                ws_prop = sheet.worksheet("Propuestas")
                prop_data = ws_prop.get_all_values()
                if len(prop_data) <= 1:
                    st.info("No hay propuestas pendientes")
                else:
                    header = prop_data[0]
                    data = prop_data[1:]
                    df_prop = pd.DataFrame(data, columns=header)
                    
                    # Filtrar pendientes
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
                                
                                # Mostrar cambios propuestos
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
