import streamlit as st
import sqlite3
import pandas as pd

# Configuración de esta página específica
st.set_page_config(page_title="Administración", page_icon="⚙️", layout="centered")

st.title("⚙️ Panel de Administración")
st.info("Área restringida para la gestión interna de normativas y boletines.")

password = st.text_input("Contraseña de acceso:", type="password")

if password == "admin123":
    st.success("Acceso concedido")
    st.divider()
    
    # --- SECCIÓN 1: AGREGAR BOLETÍN ---
    st.subheader("📝 Agregar Nuevo Boletín")
    
    with st.form("form_nuevo_boletin"):
        conn_admin = sqlite3.connect('asistente_farmacia.db')
        df_os = pd.read_sql_query("SELECT id_obra_social, nombre_os FROM obra_social", conn_admin)
        
        mapa_os = dict(zip(df_os['nombre_os'], df_os['id_obra_social']))
        
        os_seleccionada_admin = st.selectbox("Obra Social afectada:", options=list(mapa_os.keys()))
        tipo_alerta = st.selectbox("Nivel de Alerta:", options=["informativa", "advertencia", "critica"])
        mensaje_boletin = st.text_area("Mensaje de la normativa:")
        
        btn_guardar = st.form_submit_button("Guardar Boletín")
        
        if btn_guardar:
            if mensaje_boletin.strip() == "":
                st.error("El mensaje no puede estar vacío.")
            else:
                id_os = mapa_os[os_seleccionada_admin]
                cursor_insert = conn_admin.cursor()
                cursor_insert.execute("""
                    INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia)
                    VALUES (?, ?, ?, date('now', 'localtime'))
                """, (id_os, tipo_alerta, mensaje_boletin))
                conn_admin.commit()
                st.success("✅ ¡Boletín guardado! Los mostradores ya verán la alerta actualizada.")
                st.rerun() # Recarga la página automáticamente para actualizar la tabla de abajo

    st.divider()

    # --- SECCIÓN 2: VER Y ELIMINAR BOLETINES ---
    st.subheader("🗑️ Gestionar Boletines Activos")
    
    # Extraemos los boletines actuales cruzando los datos con el nombre de la obra social
    df_boletines = pd.read_sql_query("""
        SELECT 
            b.id_boletin AS 'ID', 
            o.nombre_os AS 'Obra Social', 
            b.tipo_alerta AS 'Alerta', 
            b.mensaje AS 'Mensaje', 
            b.fecha_vigencia AS 'Fecha'
        FROM boletin_os b
        JOIN obra_social o ON b.id_obra_social = o.id_obra_social
    """, conn_admin)
    
    if df_boletines.empty:
        st.info("No hay boletines generales activos en este momento.")
    else:
        # Mostramos la tabla para que puedas ver qué hay cargado (y sus IDs)
        st.dataframe(df_boletines, use_container_width=True, hide_index=True)
        
        # Pequeño formulario para eliminar
        col1, col2 = st.columns([1, 2])
        with col1:
            id_eliminar = st.number_input("Ingresa el ID a eliminar:", min_value=0, step=1)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True) # Alinea el botón con el input
            if st.button("🗑️ Eliminar Boletín"):
                if id_eliminar > 0:
                    cursor_del = conn_admin.cursor()
                    cursor_del.execute("DELETE FROM boletin_os WHERE id_boletin = ?", (id_eliminar,))
                    conn_admin.commit()
                    st.success(f"Boletín {id_eliminar} eliminado correctamente.")
                    st.rerun() # Recarga la página para mostrar la tabla actualizada
                else:
                    st.warning("Por favor, ingresa un ID válido.")
                    
    conn_admin.close()

elif password != "":
    st.error("❌ Contraseña incorrecta")
    