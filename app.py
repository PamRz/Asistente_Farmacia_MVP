import streamlit as st
import sqlite3
import pandas as pd

# Configuración de la página
st.set_page_config(
    page_title="El Asistente de Farmacia",
    page_icon="💊",
    layout="centered"
)

# Encabezado y Escudo Legal
st.title("💊 El Asistente de Farmacia")
st.warning("⚠️ **Aviso Legal:** Herramienta de consulta preventiva basada en boletines oficiales. La validación en el sistema oficial y la dispensa final son responsabilidad exclusiva del profesional de mostrador.")

# Función para extraer los datos de SQLite
@st.cache_data 
def cargar_datos():
    conexion = sqlite3.connect('asistente_farmacia.db')
    consulta = """
    SELECT 
        o.nombre_os AS 'Obra Social', 
        m.nombre_droga AS 'Medicamento', 
        r.cobertura_porcentaje AS 'Cobertura (%)', 
        r.requiere_token AS 'Requiere Token', 
        r.tope_envases AS 'Tope de Envases', 
        r.requisito_observacion AS 'Requisitos Extras'
    FROM regla_validacion r
    JOIN obra_social o ON r.id_obra_social = o.id_obra_social
    JOIN medicamento m ON r.id_medicamento = m.id_medicamento
    """
    df = pd.read_sql_query(consulta, conexion)
    conexion.close()
    return df

df_normativas = cargar_datos()

# Interfaz de Búsqueda
st.subheader("Buscador de Normativas")
col1, col2 = st.columns(2)

with col1:
    lista_obras_sociales = df_normativas['Obra Social'].unique()
    os_seleccionada = st.selectbox("Seleccione la Obra Social:", options=["-"] + list(lista_obras_sociales))

with col2:
    lista_medicamentos = df_normativas['Medicamento'].unique()
    droga_seleccionada = st.selectbox("Seleccione el Medicamento:", options=["-"] + list(lista_medicamentos))

# Lógica de Filtrado y Resultados insensible a mayúsculas/minúsculas
if os_seleccionada != "-" and droga_seleccionada != "-":
    resultado = df_normativas[
        (df_normativas['Obra Social'].str.lower() == os_seleccionada.lower()) & 
        (df_normativas['Medicamento'].str.lower() == droga_seleccionada.lower())
    ]

    
    st.divider()
    
    if not resultado.empty:
        st.success(f"✅ Normativa encontrada para **{droga_seleccionada}** por **{os_seleccionada}**")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="Cobertura", value=f"{resultado.iloc[0]['Cobertura (%)']}%")
        m2.metric(label="Tope Envases", value=resultado.iloc[0]['Tope de Envases'])
        m3.metric(label="Requiere Token", value=resultado.iloc[0]['Requiere Token'])
        
        observacion = resultado.iloc[0]['Requisitos Extras']
        st.info(f"📋 **Requisitos de Auditoría:** \n\n {observacion}")
        
    else:
        st.error(f"❌ El medicamento **{droga_seleccionada}** no registra cobertura bajo la obra social **{os_seleccionada}** en la base de datos actual.")

st.divider()

# Módulo de Alertas Sanitarias ANMAT
st.subheader("⚠️ Alertas ANMAT Activas")
conexion_anmat = sqlite3.connect('asistente_farmacia.db')
df_alertas = pd.read_sql_query("SELECT producto, lote, vencimiento, accion_requerida FROM alerta_anmat", conexion_anmat)
conexion_anmat.close()
st.dataframe(df_alertas, use_container_width=True, hide_index=True)