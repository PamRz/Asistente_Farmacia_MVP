import sqlite3
from contextlib import closing
import pandas as pd
import streamlit as st
from pathlib import Path
import base64  # <-- NUEVA LIBRERÍA PARA LEER LA IMAGEN

# Ruta absoluta indestructible
DB_PATH = Path(__file__).resolve().parent / "asistente_farmacia.db"

# Links a los vademécums oficiales
VADEMECUMS = {
    "IOMA": "https://sistemas.ioma.gba.gov.ar/vademecum/",
    "PAMI": "https://datos.pami.org.ar/dataset/medicamentos-para-afiliados/archivo/92ad6862-af8e-4047-b2cb-4bfef705feb3?view_id=27ad8972-05b6-47b5-9236-c2d8cc2bbd2d",
}

# Tipo de alerta -> (función de Streamlit, ícono)
ESTILOS_ALERTA = {
    "critica": (st.error, "🚨"),
    "informativa": (st.info, "ℹ️"),
    "advertencia": (st.warning, "⚠️"),
}

# 1. CAMBIO DE IDENTIDAD (Planilla con lápiz)
st.set_page_config(page_title="FarmaCheck", page_icon="📝", layout="wide")

# ==========================================
# NUEVO: INYECCIÓN DE IMAGEN DE FONDO
# ==========================================
def agregar_fondo(ruta_imagen):
    try:
        with open(ruta_imagen, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url(data:image/jpeg;base64,{encoded_string});
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        pass # Si no encuentra la imagen, la app sigue funcionando normal sin romperse

# Aplicamos el fondo usando nuestra ruta absoluta indestructible
RUTA_FONDO = Path(__file__).resolve().parent / "fondo.jpeg"
agregar_fondo(RUTA_FONDO)


# 2. INYECCIÓN CSS PARA AUMENTAR TAMAÑOS (Punto 2)
st.markdown("""
<style>
/* Aumentar letra del botón del Vademécum */
[data-testid="stLinkButton"] p {
    font-size: 1.15rem !important;
    font-weight: 600 !important;
}
/* Aumentar letra del título de la lista desplegable (Expander) */
[data-testid="stExpander"] summary p {
    font-size: 1.15rem !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📝 FarmaCheck")
st.warning(
    "⚠️ **Aviso Legal:** Herramienta de consulta preventiva basada en boletines oficiales. "
    "La validación en el sistema oficial y la dispensa final son responsabilidad exclusiva "
    "del profesional de mostrador."
)

# ==========================================
# ACCESO A DATOS
# ==========================================
def consultar(sql, params=()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        return conn.execute(sql, params).fetchall()

def consultar_df(sql, params=()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        return pd.read_sql_query(sql, conn, params=params)

@st.cache_data(ttl=300)
def cargar_datos():
    return consultar_df("""
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
    """)

def cargar_alertas_anmat():
    return consultar_df(
        "SELECT producto, lote, vencimiento, accion_requerida FROM alerta_anmat"
    )

def obtener_boletines_activos(nombre_os, nombre_droga):
    return consultar("""
        SELECT b.tipo_alerta, b.mensaje, b.fecha_vigencia, m.nombre_droga
        FROM boletin_os b
        JOIN obra_social o ON b.id_obra_social = o.id_obra_social
        LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
        WHERE o.nombre_os = ?
          AND b.estado = 'activo'
          AND (m.nombre_droga = ? OR b.id_medicamento IS NULL)
        ORDER BY
          CASE b.tipo_alerta
            WHEN 'critica' THEN 1
            WHEN 'advertencia' THEN 2
            WHEN 'informativa' THEN 3
            ELSE 4
          END
    """, (nombre_os, nombre_droga))

def drogas_con_boletin_activo(nombre_os):
    filas = consultar("""
        SELECT DISTINCT m.nombre_droga
        FROM boletin_os b
        JOIN obra_social o ON b.id_obra_social = o.id_obra_social
        JOIN medicamento m ON b.id_medicamento = m.id_medicamento
        WHERE o.nombre_os = ? AND b.estado = 'activo'
    """, (nombre_os,))
    return [f[0] for f in filas]

# ==========================================
# FORMATO Y COMPONENTES VISUALES
# ==========================================
def formato_moneda(valor, cero_es_sin_dato=False):
    if pd.isna(valor) or (cero_es_sin_dato and valor == 0):
        return "s/d"
    texto = f"{valor:,.2f}"
    return "$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")

def mostrar_alerta(tipo, texto):
    funcion, icono = ESTILOS_ALERTA.get(tipo, (st.warning, "⚠️"))
    funcion(texto, icon=icono)

def mostrar_alertas(alertas, columnas=2):
    cols = st.columns(columnas)
    for i, (tipo, mensaje, fecha) in enumerate(alertas):
        with cols[i % columnas]:
            mostrar_alerta(tipo, f"**{mensaje}**  \n*(Vigente desde: {fecha})*")

def tabla_catalogo(resultado):
    tabla = pd.DataFrame({
        "Marca": resultado["Marca"],
        "Presentación": resultado["Presentación"],
        "Precio ($)": resultado["Precio ($)"].apply(lambda v: formato_moneda(v, cero_es_sin_dato=True)),
        "Monto OS ($)": resultado["Monto OS ($)"].apply(lambda v: formato_moneda(v, cero_es_sin_dato=True)),
        "Copago ($)": resultado["Copago ($)"].apply(formato_moneda),
        "Cobertura (%)": resultado["Cobertura (%)"].apply(lambda v: "s/d" if pd.isna(v) else f"{int(v)} %"),
        "Laboratorio": resultado["Laboratorio"],
    })
    return tabla

# ==========================================
# LAYOUT DE COLUMNAS MAESTRAS
# ==========================================
df_normativas = cargar_datos()

col_izq, col_der = st.columns([1, 1])

with col_izq:
    lista_os = sorted(df_normativas["Obra Social"].unique())
    os_seleccionada = st.selectbox("Obra Social:", options=["-"] + lista_os)

    if os_seleccionada == "-":
        opciones_drogas = []
    else:
        con_cobertura = df_normativas.loc[
            df_normativas["Obra Social"] == os_seleccionada, "Medicamento"
        ].tolist()
        opciones_drogas = sorted(
            set(con_cobertura) | set(drogas_con_boletin_activo(os_seleccionada)),
            key=str.lower,
        )
        
    droga_seleccionada = st.selectbox(
        "Medicamento:",
        options=["-"] + opciones_drogas,
        disabled=(os_seleccionada == "-"),
    )

    url_vademecum = VADEMECUMS.get(os_seleccionada.upper())
    if url_vademecum:
        st.link_button(f"🔗 Verificar en el Vademécum Oficial de {os_seleccionada}", url_vademecum)

# 1. Cargamos alertas de la OS si hay una búsqueda activa
if os_seleccionada != "-" and droga_seleccionada != "-":
    boletines = obtener_boletines_activos(os_seleccionada, droga_seleccionada)
    alertas_generales = [(t, m, f) for t, m, f, droga in boletines if not droga]
    alertas_especificas = [(t, m, f) for t, m, f, droga in boletines if droga]

    resultado = df_normativas[
        (df_normativas["Obra Social"] == os_seleccionada)
        & (df_normativas["Medicamento"] == droga_seleccionada)
    ]

    with col_izq:
        if alertas_especificas:
            st.markdown(f"### 💊 Alerta para {droga_seleccionada}")
            mostrar_alertas(alertas_especificas, columnas=1)
            
        if not resultado.empty:
            requisitos = resultado["Requisitos Extras"].dropna().unique()
            if len(requisitos) > 0:
                lista = "\n".join(f"• {r}" for r in requisitos)
                st.info(f"📋 **Requisitos de Auditoría:**\n\n{lista}")

    with col_der:
        if alertas_generales:
            with st.expander(f"📢 Ver normativas generales de {os_seleccionada}", expanded=False):
                mostrar_alertas(alertas_generales, columnas=1)

# 2. Cargamos SIEMPRE las alertas de ANMAT en la columna derecha (debajo de las de OS)
with col_der:
    df_alertas = cargar_alertas_anmat()
    with st.expander("⚠️ Ver Alertas Sanitarias ANMAT", expanded=False):
        if df_alertas.empty:
            st.info("No hay alertas de ANMAT registradas actualmente.")
        else:
            st.dataframe(df_alertas, width="stretch", hide_index=True)

# 3. Finalmente, dibujamos la planilla abajo de todo, ocupando el ancho completo
if os_seleccionada != "-" and droga_seleccionada != "-":
    st.divider()
    
    if resultado.empty:
        st.error(
            f"❌ El medicamento **{droga_seleccionada}** no registra cobertura "
            f"bajo la obra social **{os_seleccionada}**."
        )
    else:
        st.success(f"✅ Catálogo encontrado para **{droga_seleccionada}** por **{os_seleccionada}**")
        
        df_mostrar = tabla_catalogo(resultado)
        
        columnas_ordenadas = ['Laboratorio', 'Marca', 'Presentación', 'Cobertura (%)', 'Precio ($)', 'Monto OS ($)', 'Copago ($)']
        columnas_finales = [col for col in columnas_ordenadas if col in df_mostrar.columns]
        df_mostrar = df_mostrar[columnas_finales]

        texto_busqueda = st.text_input("🔍 Buscador de medicamentos:", placeholder="Escribe aquí para filtrar la tabla...")

        if texto_busqueda:
            mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(texto_busqueda, case=False)).any(axis=1)
            df_filtrado = df_mostrar[mask]
        else:
            df_filtrado = df_mostrar

        st.dataframe(
            df_filtrado,
            height=140,
            width="stretch",
            hide_index=True
        )
        st.caption(f"📅 **Última actualización de catálogo:** {resultado['Fecha de Carga'].max()}")