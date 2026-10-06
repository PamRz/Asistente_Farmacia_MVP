import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# CORRECCIÓN DE RUTA: Como el archivo está en la raíz, usamos solo un .parent
DB_PATH = Path(__file__).resolve().parent / "asistente_farmacia.db"

# Configuración de esta página
st.set_page_config(page_title="Panel de Control Local", page_icon="⚙️", layout="wide")

st.title("⚙️ Panel de Control Local")
st.info("Entorno de administración seguro (Ejecución exclusiva en estación de trabajo local).")
st.caption(f"Base de datos conectada en: {DB_PATH}")
st.divider()
    
# --- CREACIÓN DE PESTAÑAS DE NAVEGACIÓN ---
tab1, tab2, tab3, tab4 = st.tabs(["📢 Boletines Generales / Específicos", "💊 Catálogo Completo", "⚠️ Alertas ANMAT", "🧪 Simulador de Mostrador"])
    
# ==========================================
# PESTAÑA 1: BOLETINES
# ==========================================
with tab1:
    st.subheader("📝 Agregar Nuevo Boletín")
    with st.form("form_nuevo_boletin"):
        conn_listas = sqlite3.connect(DB_PATH)
        
        df_os = pd.read_sql_query("SELECT id_obra_social, nombre_os FROM obra_social", conn_listas)
        mapa_os = dict(zip(df_os['nombre_os'], df_os['id_obra_social']))
        
        df_meds = pd.read_sql_query("SELECT id_medicamento, nombre_droga FROM medicamento ORDER BY nombre_droga", conn_listas)
        mapa_meds = dict(zip(df_meds['nombre_droga'], df_meds['id_medicamento']))
        
        conn_listas.close()
        
        os_seleccionada_admin = st.selectbox("Obra Social afectada:", options=list(mapa_os.keys()))
        
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
                try:
                    id_os = mapa_os[os_seleccionada_admin]
                    id_med = mapa_meds.get(med_seleccionado_admin, None) 
                    
                    conn_insert = sqlite3.connect(DB_PATH)
                    conn_insert.execute("PRAGMA foreign_keys = ON")
                    cursor = conn_insert.cursor()
                    cursor.execute("""
                        INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia, estado, id_medicamento)
                        VALUES (?, ?, ?, date('now', 'localtime'), ?, ?)
                    """, (id_os, tipo_alerta, mensaje_boletin, estado_alerta, id_med))
                    conn_insert.commit()
                    
                    if cursor.rowcount > 0:
                        st.success("✅ ¡Boletín guardado exitosamente en la base de datos! (Presiona F5 para refrescar la tabla)")
                    else:
                        st.error("⚠️ El comando se ejecutó, pero no se guardaron filas.")
                except Exception as e:
                    st.error(f"❌ ERROR CRÍTICO DE BASE DE DATOS: {e}")
                finally:
                    conn_insert.close()

    st.divider()
    st.subheader("🗑️ Gestionar Boletines Activos y Borradores")
    
    conn_boletines = sqlite3.connect(DB_PATH)
    df_boletines = pd.read_sql_query("""
        SELECT b.id_boletin AS 'ID', o.nombre_os AS 'Obra Social', 
               COALESCE(m.nombre_droga, 'GENERAL') AS 'Alcance / Droga',
               b.tipo_alerta AS 'Alerta', b.mensaje AS 'Mensaje', 
               b.estado AS 'Estado', b.fecha_vigencia AS 'Fecha'
        FROM boletin_os b 
        JOIN obra_social o ON b.id_obra_social = o.id_obra_social
        LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
    """, conn_boletines)
    conn_boletines.close()
    
    if df_boletines.empty:
        st.info("No hay boletines registrados.")
    else:
        st.dataframe(df_boletines, width="stretch", hide_index=True)
        
        opciones_id = ["-"] + df_boletines['ID'].astype(str).tolist()
        
        st.markdown("### 🗑️ Eliminar Boletín")
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            id_eliminar = st.selectbox("Selecciona el ID a eliminar:", options=opciones_id)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            seguro_borrar = st.checkbox("Confirmar borrado", key="chk_boletin")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Eliminar Definitivamente", disabled=(id_eliminar == "-" or not seguro_borrar)):
                try:
                    conn_del = sqlite3.connect(DB_PATH)
                    conn_del.execute("PRAGMA foreign_keys = ON")
                    cursor = conn_del.cursor()
                    cursor.execute("DELETE FROM boletin_os WHERE id_boletin = ?", (id_eliminar,))
                    conn_del.commit()
                    
                    if cursor.rowcount > 0:
                        st.success(f"✅ Boletín {id_eliminar} eliminado. (Presiona F5 para refrescar la tabla)")
                    else:
                        st.warning("El ID no existía.")
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
                finally:
                    conn_del.close()
 
# --------------------------------------------------------
# NUEVO: SECCIÓN DE EDICIÓN DE BOLETINES (PUNTO F)
# --------------------------------------------------------
st.divider()
st.markdown("### ✏️ Editar Boletín Existente")
            
        # Reutilizamos la lista opciones_id que ya creamos arriba
id_editar = st.selectbox("Selecciona el ID a editar:", options=opciones_id, key="sel_editar_bol")
            
if id_editar != "-":
            # Extraemos los datos actuales de ese boletín desde el DataFrame que ya tenemos en memoria
     bol_actual = df_boletines[df_boletines['ID'] == int(id_editar)].iloc[0]
            
     with st.form("form_editar_boletin"):
         st.info(f"Modificando normativas para: **{bol_actual['Obra Social']} ({bol_actual['Alcance / Droga']})**")
                
                # Pre-cargamos los valores actuales para que no tengas que escribir todo de nuevo
         tipos_alerta = ["informativa", "advertencia", "critica"]
         idx_alerta = tipos_alerta.index(bol_actual['Alerta']) if bol_actual['Alerta'] in tipos_alerta else 0
         nuevo_tipo = st.selectbox("Nivel de Alerta:", options=tipos_alerta, index=idx_alerta)
                
         estados = ["borrador", "activo"]
         idx_estado = estados.index(bol_actual['Estado']) if bol_actual['Estado'] in estados else 0
         nuevo_estado = st.radio("Estado de publicación:", options=estados, index=idx_estado, horizontal=True)
                
         nuevo_mensaje = st.text_area("Mensaje de la normativa:", value=bol_actual['Mensaje'])
                
         if st.form_submit_button("💾 Guardar Cambios"):
             if nuevo_mensaje.strip() == "":
                        st.error("El mensaje no puede estar vacío.")
             else:
                 try:
                     conn_upd = sqlite3.connect(DB_PATH)
                     conn_upd.execute("PRAGMA foreign_keys = ON")
                     cursor_upd = conn_upd.cursor()
                     cursor_upd.execute("""
                         UPDATE boletin_os 
                         SET tipo_alerta = ?, estado = ?, mensaje = ?
                         WHERE id_boletin = ?
                         """, (nuevo_tipo, nuevo_estado, nuevo_mensaje, id_editar))
                     conn_upd.commit()
                            
                     if cursor_upd.rowcount > 0:
                                st.success(f"✅ ¡Boletín {id_editar} actualizado! (Presiona F5 para ver los cambios)")
                     else:
                                st.error("No se pudo actualizar el registro.")
                 except Exception as e:
                            st.error(f"Error en la base de datos: {e}")
                 finally:
                            conn_upd.close()


# ==========================================
# PESTAÑA 2: CATÁLOGO DE MEDICAMENTOS
# ==========================================

with tab2:
    st.subheader("💊 Base de Datos: Reglas de Validación y Catálogo")
    conn_cat = sqlite3.connect(DB_PATH)
    df_catalogo = pd.read_sql_query("""
        SELECT o.nombre_os AS 'Obra Social', m.nombre_droga AS 'Principio Activo', 
               r.marca_comercial AS 'Marca', r.presentacion AS 'Presentación',
               r.precio_venta AS 'Precio ($)', r.cobertura_porcentaje AS 'Cobertura (%)',
               r.copago AS 'Copago ($)', r.requisito_observacion AS 'Auditoría / Requisitos'
        FROM regla_validacion r
        JOIN obra_social o ON r.id_obra_social = o.id_obra_social
        JOIN medicamento m ON r.id_medicamento = m.id_medicamento
    """, conn_cat)
    conn_cat.close()
    
    # La idea de VS Code, pero aplicada correctamente con if/else
    if df_catalogo.empty:
        st.info("No hay reglas de validación registradas en el catálogo.")
    else:
        st.dataframe(df_catalogo, width="stretch", hide_index=True)

# ==========================================
# PESTAÑA 3: ALERTAS ANMAT
# ==========================================
with tab3:
    st.subheader("⚠️ Base de Datos: Alertas Sanitarias ANMAT")
    conn_anmat = sqlite3.connect(DB_PATH)
    df_anmat = pd.read_sql_query("SELECT id_alerta AS 'ID', producto AS 'Producto', lote AS 'Lote', vencimiento AS 'Vencimiento', accion_requerida AS 'Acción Requerida' FROM alerta_anmat", conn_anmat)
    conn_anmat.close()
    
    if df_anmat.empty:
        st.info("No hay alertas de ANMAT registradas actualmente.")
    else:
        st.dataframe(df_anmat, width="stretch", hide_index=True)
        
        opciones_id_anmat = ["-"] + df_anmat['ID'].astype(str).tolist()
        
        st.markdown("### 🗑️ Eliminar Alerta Duplicada / Obsoleta")
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            id_eliminar_anmat = st.selectbox("Selecciona el ID a eliminar:", options=opciones_id_anmat, key="del_anmat_sel")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            seguro_borrar_anmat = st.checkbox("Confirmar borrado", key="chk_anmat")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Eliminar Definitivamente", key="btn_del_definitivo_anmat", disabled=(id_eliminar_anmat == "-" or not seguro_borrar_anmat)):
                try:
                    conn_del_anmat = sqlite3.connect(DB_PATH)
                    conn_del_anmat.execute("PRAGMA foreign_keys = ON")
                    cursor_anmat = conn_del_anmat.cursor()
                    cursor_anmat.execute("DELETE FROM alerta_anmat WHERE id_alerta = ?", (id_eliminar_anmat,))
                    conn_del_anmat.commit()
                    
                    if cursor_anmat.rowcount > 0:
                        st.success(f"✅ Alerta {id_eliminar_anmat} eliminada. (Presiona F5 para refrescar la tabla)")
                    else:
                        st.warning("El ID no existía.")
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
                finally:
                    conn_del_anmat.close()

# ==========================================
# PESTAÑA 4: SIMULADOR DE MOSTRADOR
# ==========================================
with tab4:
    st.subheader("🧪 Simulador de Mostrador (Vista Previa)")
    
    if st.button("🔄 Actualizar Simulador"):
        st.rerun()
        
    st.info("Simula una búsqueda exacta. Mostrará alertas Generales de la OS + Alertas Específicas de la droga.")
       
    conn_sim = sqlite3.connect(DB_PATH)
    df_os_sim = pd.read_sql_query("SELECT nombre_os FROM obra_social", conn_sim)
    lista_os_sim = ["-"] + df_os_sim['nombre_os'].tolist()
    
    df_drogas_sim = pd.read_sql_query("SELECT nombre_droga FROM medicamento ORDER BY nombre_droga", conn_sim)
    lista_drogas_sim = ["-"] + df_drogas_sim['nombre_droga'].tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        os_simulada = st.selectbox("Simular Obra Social:", options=lista_os_sim)
    with col2:
        droga_simulada = st.selectbox("Simular Medicamento:", options=lista_drogas_sim)
        
    if os_simulada != "-" and droga_simulada != "-":
        cursor_sim = conn_sim.cursor()
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
    conn_sim.close()
