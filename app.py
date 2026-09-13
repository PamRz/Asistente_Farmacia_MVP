import streamlit as st
import sqlite3
import pandas as pd

# Configuración básica de la página
st.set_page_config(page_title="Asistente de Farmacia", page_icon="💊", layout="centered")

st.title("💊 Validador de Cobertura Farmacéutica")
st.markdown("Consulta rápida de normativas, coberturas y alertas epidemiológicas.")

# Función para conectar a la base de datos (pip install streamlit)
@st.cache_resource
def crear_conexion():
    return sqlite3.connect('asistente_farmacia.db', check_same_thread=False)

conn = crear_conexion()

# Extraemos los datos para armar los menús desplegables
df_obras_sociales = pd.read_sql_query("SELECT id_obra_social, nombre_os FROM obra_social", conn)
df_medicamentos = pd.read_sql_query("SELECT id_medicamento, nombre_droga FROM medicamento ORDER BY nombre_droga", conn)

st.subheader("🔍 Consulta de Vademécum")
col1, col2 = st.columns(2)

with col1:
    os_elegida = st.selectbox("Obra Social", df_obras_sociales['nombre_os'])

with col2:
    droga_elegida = st.selectbox("Droga / Principio Activo", df_medicamentos['nombre_droga'])

# Botón de validación
if st.button("Validar Cobertura", type="primary"):
    # Obtenemos los IDs reales basados en la selección del usuario
    id_os = df_obras_sociales.loc[df_obras_sociales['nombre_os'] == os_elegida, 'id_obra_social'].iloc[0]
    id_med = df_medicamentos.loc[df_medicamentos['nombre_droga'] == droga_elegida, 'id_medicamento'].iloc[0]
    
    # Consultamos la regla de negocio
    query = """
    SELECT cobertura_porcentaje, requiere_token, tope_envases, requisito_observacion 
    FROM regla_validacion 
    WHERE id_obra_social = ? AND id_medicamento = ?
    """
    df_regla = pd.read_sql_query(query, conn, params=(int(id_os), int(id_med)))
    
    if not df_regla.empty:
        st.success("✅ Cobertura Autorizada")
        
        # Tarjetas visuales para los datos principales
        metrica1, metrica2, metrica3 = st.columns(3)
        metrica1.metric(label="Cobertura", value=f"{df_regla['cobertura_porcentaje'].iloc[0]}%")
        metrica2.metric(label="Tope Envases", value=f"{df_regla['tope_envases'].iloc[0]}")
        metrica3.metric(label="Requiere Token", value=f"{df_regla['requiere_token'].iloc[0]}")
        
        st.info(f"**Requisitos y Observaciones:** {df_regla['requisito_observacion'].iloc[0]}")
    else:
        st.error("❌ El medicamento seleccionado NO posee cobertura para esta Obra Social o se encuentra fuera de vademécum.")

st.divider()

# Módulo de Alertas Sanitarias
st.subheader("⚠️ Alertas ANMAT Activas")
df_alertas = pd.read_sql_query("SELECT producto, lote, vencimiento, accion_requerida FROM alerta_anmat", conn)
st.dataframe(df_alertas, use_container_width=True, hide_index=True)