import streamlit as st
import sqlite3
import pandas as pd

# Configuración de esta página (ahora en modo 'wide' para ver mejor los datos)
st.set_page_config(page_title="Administración", page_icon="⚙️", layout="wide")

st.title("⚙️ Panel de Administración y Auditoría")
st.info("Área restringida para la gestión integral de la base de datos.")

password = st.text_input("Contraseña de acceso:", type="password")

if password == "admin123":
    st.success("Acceso concedido")
    st.divider()
    
    # --- CREACIÓN DE PESTAÑAS DE NAVEGACIÓN ---
    tab1, tab2, tab3 = st.tabs(["📢 Boletines Generales", "💊 Catálogo Completo (IOMA/PAMI)", "⚠️ Alertas ANMAT"])
    
    # ==========================================
    # PESTAÑA 1: BOLETINES GENERALES
    # ==========================================
    with tab1:
        st.subheader("📝 Agregar Nuevo Boletín")
        with st.form("form_nuevo_boletin"):
            conn = sqlite3.connect('asistente_farmacia.db')
            df_os = pd.read_sql_query("SELECT id_obra_social, nombre_os FROM obra_social", conn)
            mapa_os = dict(zip(df_os['nombre_os'], df_os['id_obra_social']))
            
            os_seleccionada_admin = st.selectbox("Obra Social afectada:", options=list(mapa_os.keys()))
            tipo_alerta = st.selectbox("Nivel de Alerta:", options=["informativa", "advertencia", "critica"])
            mensaje_boletin = st.text_area("Mensaje de la normativa (Ej: Se requiere receta electrónica...):")
            
            btn_guardar = st.form_submit_button("Guardar Boletín")
            
            if btn_guardar:
                if mensaje_boletin.strip() == "":
                    st.error("El mensaje no puede estar vacío.")
                else:
                    id_os = mapa_os[os_seleccionada_admin]
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia)
                        VALUES (?, ?, ?, date('now', 'localtime'))
                    """, (id_os, tipo_alerta, mensaje_boletin))
                    conn.commit()
                    st.success("✅ ¡Boletín guardado exitosamente!")
                    st.rerun()

        st.divider()
        st.subheader("🗑️ Gestionar Boletines Activos")
        df_boletines = pd.read_sql_query("""
            SELECT b.id_boletin AS 'ID', o.nombre_os AS 'Obra Social', b.tipo_alerta AS 'Alerta', 
                   b.mensaje AS 'Mensaje', b.fecha_vigencia AS 'Fecha'
            FROM boletin_os b JOIN obra_social o ON b.id_obra_social = o.id_obra_social
        """, conn)
        
        if df_boletines.empty:
            st.info("No hay boletines generales activos en este momento.")
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
    # PESTAÑA 2: CATÁLOGO DE MEDICAMENTOS (Auditoría)
    # ==========================================
    with tab2:
        st.subheader("💊 Base de Datos: Reglas de Validación y Catálogo")
        st.info("Vista de auditoría: Aquí puedes verificar los miles de medicamentos y requisitos específicos cargados.")
        
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
        
        # Streamlit maneja automáticamente la paginación para tablas grandes
        st.dataframe(df_catalogo, use_container_width=True, hide_index=True)

    # ==========================================
    # PESTAÑA 3: ALERTAS ANMAT
    # ==========================================
    with tab3:
        st.subheader("⚠️ Base de Datos: Alertas Sanitarias ANMAT")
        
        conn = sqlite3.connect('asistente_farmacia.db')
        df_anmat = pd.read_sql_query("""
            SELECT id_alerta AS 'ID', producto AS 'Producto', lote AS 'Lote', 
                   vencimiento AS 'Vencimiento', accion_requerida AS 'Acción Requerida' 
            FROM alerta_anmat
        """, conn)
        conn.close()
        
        if df_anmat.empty:
            st.info("No hay alertas de ANMAT registradas actualmente.")
        else:
            st.dataframe(df_anmat, use_container_width=True, hide_index=True)

elif password != "":
    st.error("❌ Contraseña incorrecta")
    