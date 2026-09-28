import streamlit as st
import sqlite3
import pandas as pd

# Configuración de esta página
st.set_page_config(page_title="Administración", page_icon="⚙️", layout="wide")

st.title("⚙️ Panel de Administración y Auditoría")
st.info("Área restringida para la gestión integral de la base de datos.")

password = st.text_input("Contraseña de acceso:", type="password")

if password == "admin123":
    st.success("Acceso concedido")
    st.divider()
    
    # --- CREACIÓN DE PESTAÑAS DE NAVEGACIÓN ---
    tab1, tab2, tab3, tab4 = st.tabs(["📢 Boletines Generales / Específicos", "💊 Catálogo Completo", "⚠️ Alertas ANMAT", "🧪 Simulador de Mostrador"])
    
    # ==========================================
    # PESTAÑA 1: BOLETINES
    # ==========================================
    with tab1:
        st.subheader("📝 Agregar Nuevo Boletín")
        with st.form("form_nuevo_boletin"):
            conn = sqlite3.connect('asistente_farmacia.db')
            
            # Cargar Obras Sociales
            df_os = pd.read_sql_query("SELECT id_obra_social, nombre_os FROM obra_social", conn)
            mapa_os = dict(zip(df_os['nombre_os'], df_os['id_obra_social']))
            
            # Cargar Medicamentos para el filtro específico
            df_meds = pd.read_sql_query("SELECT id_medicamento, nombre_droga FROM medicamento ORDER BY nombre_droga", conn)
            mapa_meds = dict(zip(df_meds['nombre_droga'], df_meds['id_medicamento']))
            
            os_seleccionada_admin = st.selectbox("Obra Social afectada:", options=list(mapa_os.keys()))
            
            # NUEVO: Selector de medicamento (Opcional)
            opciones_med = ["-- General (Aplica a toda la Obra Social) --"] + list(mapa_meds.keys())
            med_seleccionado_admin = st.selectbox("Medicamento específico (Opcional):", options=opciones_med)
            
            tipo_alerta = st.selectbox("Nivel de Alerta:", options=["informativa", "advertencia", "critica"])
            estado_alerta = st.radio("Estado de publicación:", options=["borrador", "activo"], horizontal=True)
            mensaje_boletin = st.text_area("Mensaje de la normativa:")
            
            btn_guardar = st.form_submit_button("Guardar Boletín")
            
            if btn_guardar:
                if mensaje_boletin.strip() == "":
                    st.error("El mensaje no puede estar vacío.")
                else:
                    id_os = mapa_os[os_seleccionada_admin]
                    # Determinamos si lleva ID de medicamento o NULL
                    id_med = mapa_meds.get(med_seleccionado_admin, None) 
                    
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia, estado, id_medicamento)
                        VALUES (?, ?, ?, date('now', 'localtime'), ?, ?)
                    """, (id_os, tipo_alerta, mensaje_boletin, estado_alerta, id_med))
                    conn.commit()
                    st.success("✅ ¡Boletín guardado exitosamente!")
                    st.rerun()

        st.divider()
        st.subheader("🗑️ Gestionar Boletines Activos y Borradores")
        # Actualizamos la consulta para mostrar el medicamento (si aplica) con un LEFT JOIN
        df_boletines = pd.read_sql_query("""
            SELECT b.id_boletin AS 'ID', o.nombre_os AS 'Obra Social', 
                   COALESCE(m.nombre_droga, 'GENERAL') AS 'Alcance / Droga',
                   b.tipo_alerta AS 'Alerta', b.mensaje AS 'Mensaje', 
                   b.estado AS 'Estado', b.fecha_vigencia AS 'Fecha'
            FROM boletin_os b 
            JOIN obra_social o ON b.id_obra_social = o.id_obra_social
            LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
        """, conn)
        
        if df_boletines.empty:
            st.info("No hay boletines registrados.")
        else:
            st.dataframe(df_boletines, use_container_width=True, hide_index=True)
            col1, col2 = st.columns([1, 2])
            with col1:
                id_eliminar = st.number_input("Ingresa el ID a eliminar:", min_value=0, step=1)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Eliminar Boletín"):
                    if id_eliminar > 0:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM boletin_os WHERE id_boletin = ?", (id_eliminar,))
                        conn.commit()
                        st.success(f"Boletín {id_eliminar} eliminado.")
                        st.rerun()
                    else:
                        st.warning("Por favor, ingresa un ID válido.")
        conn.close()

    # ==========================================
    # PESTAÑA 2: CATÁLOGO DE MEDICAMENTOS
    # ==========================================
    with tab2:
        st.subheader("💊 Base de Datos: Reglas de Validación y Catálogo")
        conn = sqlite3.connect('asistente_farmacia.db')
        df_catalogo = pd.read_sql_query("""
            SELECT o.nombre_os AS 'Obra Social', m.nombre_droga AS 'Principio Activo', 
                   r.marca_comercial AS 'Marca', r.presentacion AS 'Presentación',
                   r.precio_venta AS 'Precio ($)', r.cobertura_porcentaje AS 'Cobertura (%)',
                   r.copago AS 'Copago ($)', r.requisito_observacion AS 'Auditoría / Requisitos'
            FROM regla_validacion r
            JOIN obra_social o ON r.id_obra_social = o.id_obra_social
            JOIN medicamento m ON r.id_medicamento = m.id_medicamento
        """, conn)
        conn.close()
        st.dataframe(df_catalogo, use_container_width=True, hide_index=True)

    # ==========================================
    # PESTAÑA 3: ALERTAS ANMAT
    # ==========================================
    with tab3:
        st.subheader("⚠️ Base de Datos: Alertas Sanitarias ANMAT")
        conn = sqlite3.connect('asistente_farmacia.db')
        df_anmat = pd.read_sql_query("SELECT id_alerta AS 'ID', producto, lote, vencimiento, accion_requerida FROM alerta_anmat", conn)
        conn.close()
        if df_anmat.empty:
            st.info("No hay alertas de ANMAT registradas actualmente.")
        else:
            st.dataframe(df_anmat, use_container_width=True, hide_index=True)

    # ==========================================
    # PESTAÑA 4: SIMULADOR DE MOSTRADOR
    # ==========================================
    with tab4:
        st.subheader("🧪 Simulador de Mostrador (Vista Previa)")
        st.info("Simula una búsqueda exacta. Mostrará alertas Generales de la OS + Alertas Específicas de la droga.")
        
        conn = sqlite3.connect('asistente_farmacia.db')
        df_os_sim = pd.read_sql_query("SELECT nombre_os FROM obra_social", conn)
        lista_os_sim = ["-"] + df_os_sim['nombre_os'].tolist()
        
        # Traemos la lista real de medicamentos para simular el frontend
        df_drogas_sim = pd.read_sql_query("SELECT nombre_droga FROM medicamento ORDER BY nombre_droga", conn)
        lista_drogas_sim = ["-"] + df_drogas_sim['nombre_droga'].tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            os_simulada = st.selectbox("Simular Obra Social:", options=lista_os_sim)
        with col2:
            droga_simulada = st.selectbox("Simular Medicamento:", options=lista_drogas_sim)
            
        if os_simulada != "-" and droga_simulada != "-":
            cursor_sim = conn.cursor()
            
            # La nueva consulta cruza los datos de forma exacta o asume alertas generales (NULL)
            cursor_sim.execute("""
                SELECT b.tipo_alerta, b.mensaje, b.fecha_vigencia, b.estado, m.nombre_droga 
                FROM boletin_os b
                JOIN obra_social o ON b.id_obra_social = o.id_obra_social
                LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
                WHERE o.nombre_os = ? 
                  AND (m.nombre_droga = ? OR b.id_medicamento IS NULL)
            """, (os_simulada, droga_simulada))
            
            boletines_sim = cursor_sim.fetchall()
            
            if boletines_sim:
                st.markdown("### 🖥️ Así se verán las alertas para esta combinación:")
                st.markdown("<br>", unsafe_allow_html=True)
                
                for tipo_alerta, mensaje, fecha, estado, nombre_droga in boletines_sim:
                    etiqueta_estado = "👀 **[BORRADOR OCULTO]**" if estado == 'borrador' else "✅ **[ACTIVO]**"
                    etiqueta_alcance = f"📌 *(Específico para {nombre_droga})*" if nombre_droga else "🌐 *(General para toda la OS)*"
                    
                    texto_mostrar = f"{etiqueta_estado} {mensaje} \n*(Vigente desde: {fecha}) - {etiqueta_alcance}*"
                    
                    if tipo_alerta == 'critica':
                        st.error(texto_mostrar, icon="🚨")
                    elif tipo_alerta == 'informativa':
                        st.info(texto_mostrar, icon="ℹ️")
                    else:
                        st.warning(texto_mostrar, icon="⚠️")
            else:
                st.success(f"No hay normativas registradas para {os_simulada} y {droga_simulada}.")
        conn.close()

elif password != "":
    st.error("❌ Contraseña incorrecta")