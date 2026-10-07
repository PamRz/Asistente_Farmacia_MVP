import sqlite3
from contextlib import closing
import pandas as pd
import streamlit as st
from pathlib import Path

# Ruta absoluta indestructible
DB_PATH = Path(__file__).resolve().parent / "asistente_farmacia.db"

# Links a los vademécums oficiales
VADEMECUMS = {
    "IOMA": "https://sistemas.ioma.gba.gov.ar/vademecum/",
    "PAMI": "https://www.pami.org.ar/vademecum",
}

# Tipo de alerta -> (función de Streamlit, ícono)
ESTILOS_ALERTA = {
    "critica": (st.error, "🚨"),
    "informativa": (st.info, "ℹ️"),
    "advertencia": (st.warning, "⚠️"),
}

# 1. CAMBIO DE IDENTIDAD A FARMACHECK
st.set_page_config(page_title="FarmaCheck", page_icon="💊", layout="wide")

st.title("💊 FarmaCheck")
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
# 2. NUEVO DISEÑO: LAYOUT DE 2 COLUMNAS MAESTRAS
# ==========================================
df_normativas = cargar_datos()

# Creamos las dos grandes divisiones de tu dibujo
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

if os_seleccionada != "-" and droga_seleccionada != "-":
    boletines = obtener_boletines_activos(os_seleccionada, droga_seleccionada)

    alertas_generales = [(t, m, f) for t, m, f, droga in boletines if not droga]
    alertas_especificas = [(t, m, f) for t, m, f, droga in boletines if droga]

    # Ubicamos las Alertas Específicas debajo del selector (Columna Izquierda)
    with col_izq:
        if alertas_especificas:
            st.markdown(f"### 💊 Alerta para {droga_seleccionada}")
            mostrar_alertas(alertas_especificas, columnas=1)

    # Ubicamos las Alertas Generales apiladas en la Columna Derecha
    with col_der:
        if alertas_generales:
            st.markdown(f"### 📢 Alertas según {os_seleccionada}")
            mostrar_alertas(alertas_generales, columnas=1) # columnas=1 fuerza el apilamiento vertical ("jerarquía de colores")

    st.divider()

    # ==========================================
    # 3. PLANILLA CON MEDICAMENTOS Y SCROLL
    # ==========================================
    resultado = df_normativas[
        (df_normativas["Obra Social"] == os_seleccionada)
        & (df_normativas["Medicamento"] == droga_seleccionada)
    ]

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
            height=140, # ALTO REDUCIDO: Muestra aprox 3 filas y fuerza el scroll interno
            width="stretch",
            hide_index=True
        )

        requisitos = resultado["Requisitos Extras"].dropna().unique()
        if len(requisitos) > 0:
            lista = "\n".join(f"• {r}" for r in requisitos)
            st.info(f"📋 **Requisitos de Auditoría:**\n\n{lista}")

        st.caption(f"📅 **Última actualización de catálogo:** {resultado['Fecha de Carga'].max()}")

st.divider()

st.subheader("⚠️ Alertas ANMAT")
df_alertas = cargar_alertas_anmat()
if df_alertas.empty:
    st.info("No hay alertas de ANMAT registradas actualmente.")
else:
    st.dataframe(df_alertas, width="stretch", hide_index=True)