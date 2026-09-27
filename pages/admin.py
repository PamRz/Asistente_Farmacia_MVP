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
    st.subheader("📝 Agregar Nuevo Boletín")
    
    with st.form("form_nuevo_boletin"):
        # Conectamos para traer las obras sociales disponibles
        conn_admin = sqlite3.connect('asistente_farmacia.db')
        df_os = pd.read_sql_query("SELECT id_obra_social, nombre_os FROM obra_social", conn_admin)
        conn_admin.close()
        
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
                
                # Insertamos el nuevo boletín
                conn_insert = sqlite3.connect('asistente_farmacia.db')
                cursor_insert = conn_insert.cursor()
                cursor_insert.execute("""
                    INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia)
                    VALUES (?, ?, ?, date('now', 'localtime'))
                """, (id_os, tipo_alerta, mensaje_boletin))
                conn_insert.commit()
                conn_insert.close()
                
                st.success("✅ ¡Boletín guardado! Los mostradores ya verán la alerta actualizada.")
elif password != "":
    st.error("❌ Contraseña incorrecta")
    