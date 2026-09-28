import streamlit as st
import sqlite3
import pandas as pd

# Configuración de la página
st.set_page_config(
    page_title="El Asistente de Farmacia",
    page_icon="🤖",
    layout="wide"
)

# Encabezado y Escudo Legal
st.title("🤖 El Asistente de Farmacia")
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
        r.requisito_observacion AS 'Requisitos Extras',
        r.fecha_carga AS 'Fecha de Carga',
        r.presentacion AS 'Presentación',
        r.marca_comercial AS 'Marca',
        r.precio_venta AS 'Precio ($)',
        r.monto_cobertura AS 'Monto OS ($)',
        r.copago AS 'Copago ($)',
        r.laboratorio AS 'Laboratorio'
    FROM regla_validacion r
    JOIN obra_social o ON r.id_obra_social = o.id_obra_social
    JOIN medicamento m ON r.id_medicamento = m.id_medicamento
    """
    df = pd.read_sql_query(consulta, conexion)
    conexion.close()
    return df

#--------------------------------------------------------------------------
# Función EVOLUCIONADA: Obtiene boletines generales + específicos
#--------------------------------------------------------------------------
@st.cache_data(ttl=60)
def obtener_boletines_activos(nombre_os, nombre_droga):
    import sqlite3
    conn = sqlite3.connect('asistente_farmacia.db')
    cursor = conn.cursor()
    
    # La consulta bloquea los borradores (estado='activo') y cruza OS + Droga
    cursor.execute("""
        SELECT b.tipo_alerta, b.mensaje, b.fecha_vigencia, m.nombre_droga 
        FROM boletin_os b
        JOIN obra_social o ON b.id_obra_social = o.id_obra_social
        LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
        WHERE o.nombre_os = ? 
          AND b.estado = 'activo'
          AND (m.nombre_droga = ? OR b.id_medicamento IS NULL)
    """, (nombre_os, nombre_droga))
    
    boletines = cursor.fetchall()
    conn.close()
    return boletines

#----------------------------------------------------------
# Carga de Datos y Configuración de la Interfaz
#----------------------------------------------------------
df_normativas = cargar_datos()

# 1. Interfaz de Búsqueda
st.subheader("Buscador de Normativas")
col1, col2 = st.columns(2)

with col1:
    lista_obras_sociales = df_normativas['Obra Social'].unique()
    os_seleccionada = st.selectbox("Seleccione la Obra Social:", options=["-"] + list(lista_obras_sociales))

with col2:
    lista_medicamentos = df_normativas['Medicamento'].unique()
    droga_seleccionada = st.selectbox("Seleccione el Medicamento:", options=["-"] + list(lista_medicamentos))

# 2. Mostrar boletines inteligentes (Generales + Específicos)
if os_seleccionada != "-":
    # Ahora le pasamos ambas variables a la función
    boletines = obtener_boletines_activos(os_seleccionada, droga_seleccionada)
    
    if boletines:
        st.markdown("<br>", unsafe_allow_html=True)
        for tipo_alerta, mensaje, fecha, nombre_droga in boletines:
            
            # Si el boletín es específico, le agregamos el pin visual
            etiqueta_alcance = f" 📌 *(Específico para {nombre_droga})*" if nombre_droga else ""
            texto_mostrar = f"**{mensaje}**  \n*(Vigente desde: {fecha}){etiqueta_alcance}*"
            
            if tipo_alerta == 'critica':
                st.error(texto_mostrar, icon="🚨")
            elif tipo_alerta == 'informativa':
                st.info(texto_mostrar, icon="ℹ️")
            else:
                st.warning(texto_mostrar, icon="⚠️")

#---------------------------------------------------------------------
# 3. Botón dinámico para verificación directa en el sitio oficial
#---------------------------------------------------------------------
if os_seleccionada.upper() == "IOMA":
    st.link_button("🔗 Verificar en el Vademécum Oficial de IOMA", "https://sistemas.ioma.gba.gov.ar/vademecum/")
elif os_seleccionada.upper() == "PAMI":
    st.link_button("🔗 Verificar en el Vademécum Oficial de PAMI", "https://www.pami.org.ar/vademecum")

# Lógica de Filtrado y Resultados
if os_seleccionada != "-" and droga_seleccionada != "-":
    resultado = df_normativas[
        (df_normativas['Obra Social'].str.lower() == os_seleccionada.lower()) & 
        (df_normativas['Medicamento'].str.lower() == droga_seleccionada.lower())
    ]

    st.divider()
    # 4. Mostrar resultados de la base de datos
    if not resultado.empty:
        st.success(f"✅ Catálogo encontrado para **{droga_seleccionada}** por **{os_seleccionada}**")
        
        columnas_mostrar = ['Marca', 'Presentación', 'Precio ($)', 'Monto OS ($)', 'Copago ($)', 'Cobertura (%)', 'Laboratorio']
        df_mostrar = resultado[columnas_mostrar].copy()
        
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        observacion = resultado.iloc[0]['Requisitos Extras']
        st.info(f"📋 **Requisitos de Auditoría (Ficha Técnica):** \n\n {observacion}")

        fecha_registro = resultado.iloc[0]['Fecha de Carga']
        st.caption(f"📅 **Última actualización de catálogo en el sistema:** {fecha_registro}")
        
    else:
        st.error(f"❌ El medicamento **{droga_seleccionada}** no registra cobertura bajo la obra social **{os_seleccionada}** en la base de datos actual.")

st.divider()

# Módulo de Alertas Sanitarias ANMAT
st.subheader("⚠️ Alertas ANMAT Activas")
conexion_anmat = sqlite3.connect('asistente_farmacia.db')
df_alertas = pd.read_sql_query("SELECT producto, lote, vencimiento, accion_requerida FROM alerta_anmat", conexion_anmat)
conexion_anmat.close()
st.dataframe(df_alertas, use_container_width=True, hide_index=True)