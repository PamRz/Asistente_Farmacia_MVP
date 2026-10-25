# Este script implementa un panel de control local para administrar boletines, alertas ANMAT y el catálogo de medicamentos
#  en una farmacia. Utiliza Streamlit para la interfaz de usuario y SQLite para la base de datos. 
# Permite agregar, editar, eliminar (lógicamente) y restaurar registros, así como simular la visualización de alertas según
#  la obra social y el medicamento seleccionado.
import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# CORRECCIÓN DE RUTA
DB_PATH = Path(__file__).resolve().parent / "asistente_farmacia.db"

# ==========================================
# AUTO-MIGRACIÓN DE BASE DE DATOS
# ==========================================
# Agrega la columna 'estado' a alerta_anmat si no existe para permitir la Papelera
try:
    conn_mig = sqlite3.connect(DB_PATH)
    cur_mig = conn_mig.cursor()
    cur_mig.execute("PRAGMA table_info(alerta_anmat)")
    cols = [col[1] for col in cur_mig.fetchall()]
    if 'estado' not in cols:
        cur_mig.execute("ALTER TABLE alerta_anmat ADD COLUMN estado TEXT DEFAULT 'activo'")
        conn_mig.commit()
except Exception as e:
    print(f"Error en migración: {e}")
finally:
    conn_mig.close()
# ==========================================

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
    # Filtramos para NO ver los eliminados en la tabla principal
    df_boletines = pd.read_sql_query("""
        SELECT b.id_boletin AS 'ID', o.nombre_os AS 'Obra Social', 
               COALESCE(m.nombre_droga, 'GENERAL') AS 'Alcance / Droga',
               b.tipo_alerta AS 'Alerta', b.mensaje AS 'Mensaje', 
               b.estado AS 'Estado', b.fecha_vigencia AS 'Fecha'
        FROM boletin_os b 
        JOIN obra_social o ON b.id_obra_social = o.id_obra_social
        LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
        WHERE b.estado != 'eliminado'
    """, conn_boletines)
    
    if df_boletines.empty:
        st.info("No hay boletines activos ni en borrador.")
    else:
        st.dataframe(df_boletines, width="stretch", hide_index=True)
        
        opciones_id = ["-"] + df_boletines['ID'].astype(str).tolist()
        
        st.markdown("### 🗑️ Mover Boletín a la Papelera")
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            id_eliminar = st.selectbox("Selecciona el ID a enviar a papelera:", options=opciones_id, key="del_bol_sel")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            seguro_borrar = st.checkbox("Confirmar envío a papelera", key="chk_boletin")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Enviar a Papelera", key="btn_papelera_bol", disabled=(id_eliminar == "-" or not seguro_borrar)):
                try:
                    conn_del = sqlite3.connect(DB_PATH)
                    conn_del.execute("PRAGMA foreign_keys = ON")
                    cursor = conn_del.cursor()
                    # Borrado Lógico: Update estado a 'eliminado'
                    cursor.execute("UPDATE boletin_os SET estado = 'eliminado' WHERE id_boletin = ?", (id_eliminar,))
                    conn_del.commit()
                    
                    if cursor.rowcount > 0:
                        st.success(f"✅ Boletín {id_eliminar} movido a la papelera. (Presiona F5 para refrescar)")
                    else:
                        st.warning("El ID no existía.")
                except Exception as e:
                    st.error(f"Error al mover a papelera: {e}")
                finally:
                    conn_del.close()

        # --- SECCIÓN DE EDICIÓN DE BOLETINES ---
        st.divider()
        st.markdown("### ✏️ Editar Boletín Existente")
        id_editar = st.selectbox("Selecciona el ID a editar:", options=opciones_id, key="sel_editar_bol")
                    
        if id_editar != "-":
            bol_actual = df_boletines[df_boletines['ID'] == int(id_editar)].iloc[0]
                    
            with st.form("form_editar_boletin"):
                st.info(f"Modificando normativas para: **{bol_actual['Obra Social']} ({bol_actual['Alcance / Droga']})**")
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
                                st.success(f"✅ ¡Boletín {id_editar} actualizado! (Presiona F5)")
                            else:
                                st.error("No se pudo actualizar el registro.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                        finally:
                            conn_upd.close()

    # --- PAPELERA DE RECICLAJE BOLETINES ---
    st.divider()
    with st.expander("♻️ Abrir Papelera de Reciclaje (Boletines)", expanded=False):
        df_papelera_bol = pd.read_sql_query("""
            SELECT b.id_boletin AS 'ID', o.nombre_os AS 'Obra Social', 
                   COALESCE(m.nombre_droga, 'GENERAL') AS 'Alcance / Droga',
                   b.mensaje AS 'Mensaje'
            FROM boletin_os b 
            JOIN obra_social o ON b.id_obra_social = o.id_obra_social
            LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
            WHERE b.estado = 'eliminado'
        """, conn_boletines)
        
        if df_papelera_bol.empty:
            st.info("La papelera de boletines está vacía.")
        else:
            st.table(df_papelera_bol)
            opciones_restaurar_bol = ["-"] + df_papelera_bol['ID'].astype(str).tolist()
            col_r1, col_r2 = st.columns([2, 2])
            with col_r1:
                id_restaurar_bol = st.selectbox("ID a Restaurar:", options=opciones_restaurar_bol, key="sel_rest_bol")
            with col_r2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("♻️ Restaurar Boletín (a Borrador)", disabled=(id_restaurar_bol == "-")):
                    try:
                        conn_res = sqlite3.connect(DB_PATH)
                        cur_res = conn_res.cursor()
                        cur_res.execute("UPDATE boletin_os SET estado = 'borrador' WHERE id_boletin = ?", (id_restaurar_bol,))
                        conn_res.commit()
                        st.success(f"✅ Boletín {id_restaurar_bol} restaurado como borrador. (Presiona F5)")
                    except Exception as e:
                        st.error(f"Error al restaurar: {e}")
                    finally:
                        conn_res.close()
    
    conn_boletines.close()

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
    
    if df_catalogo.empty:
        st.info("No hay reglas de validación registradas en el catálogo.")
    else:
        st.dataframe(df_catalogo, width="stretch", hide_index=True)

# ==========================================
# PESTAÑA 3: ALERTAS ANMAT
# ==========================================
with tab3:
    st.subheader("➕ Agregar Nueva Alerta ANMAT")
    
    with st.form("form_nueva_anmat"):
        st.info("Ingresa los datos del producto retirado o con advertencia sanitaria.")
        nuevo_producto = st.text_input("Producto (Marca, Genérico y Presentación):", placeholder="Ej: Solución Isotónica de Cloruro de Sodio 0,9% - Rivero")
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            nuevo_lote = st.text_input("Lote(s) afectado(s):", placeholder="Ej: 70413108, 70416108 o Todos los lotes")
        with col_a2:
            nuevo_vencimiento = st.text_input("Vencimiento:", placeholder="Ej: N/A o SEP-26")
            
        nuevo_motivo = st.text_input("Motivo de la alerta:", placeholder="Ej: Baja definitiva de habilitación del laboratorio")
        nueva_accion = st.text_area("Acción Requerida:", placeholder="Ej: Abstenerse de usar y dispensar cualquier producto de la firma.")
        
        btn_guardar_anmat = st.form_submit_button("Guardar Alerta ANMAT")
        
        if btn_guardar_anmat:
            if nuevo_producto.strip() == "" or nueva_accion.strip() == "" or nuevo_motivo.strip() == "":
                st.error("❌ Los campos 'Producto', 'Motivo' y 'Acción Requerida' son obligatorios.")
            else:
                try:
                    conn_anmat_ins = sqlite3.connect(DB_PATH)
                    conn_anmat_ins.execute("PRAGMA foreign_keys = ON")
                    cursor_ins = conn_anmat_ins.cursor()
                    cursor_ins.execute("""
                        INSERT INTO alerta_anmat (producto, lote, vencimiento, motivo, accion_requerida, estado)
                        VALUES (?, ?, ?, ?, ?, 'activo')
                    """, (nuevo_producto, nuevo_lote, nuevo_vencimiento, nuevo_motivo, nueva_accion))
                    conn_anmat_ins.commit()
                    st.success("✅ ¡Alerta ANMAT guardada exitosamente! (Presiona F5 para refrescar la tabla)")
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")
                finally:
                    conn_anmat_ins.close()

    st.divider()
    st.subheader("⚠️ Base de Datos: Alertas Sanitarias ANMAT Activas")
    
    conn_anmat = sqlite3.connect(DB_PATH)
    # Filtramos para no ver las eliminadas
    df_anmat = pd.read_sql_query("""
        SELECT id_alerta AS 'ID', producto AS 'Producto', lote AS 'Lote', 
               vencimiento AS 'Vencimiento', motivo AS 'Motivo', 
               accion_requerida AS 'Acción Requerida', estado AS 'Estado' 
        FROM alerta_anmat
        WHERE estado != 'eliminado'
    """, conn_anmat)
    
    if df_anmat.empty:
        st.info("No hay alertas de ANMAT registradas actualmente.")
    else:
        st.dataframe(df_anmat, width="stretch", hide_index=True)
        
        opciones_id_anmat = ["-"] + df_anmat['ID'].astype(str).tolist()
        
        # --- ELIMINAR ANMAT (BORRADO LÓGICO) ---
        st.markdown("### 🗑️ Mover Alerta ANMAT a Papelera")
        col_del1, col_del2, col_del3 = st.columns([2, 2, 2])
        
        with col_del1:
            id_eliminar_anmat = st.selectbox("Selecciona el ID a eliminar:", options=opciones_id_anmat, key="del_anmat_sel")
        with col_del2:
            st.markdown("<br>", unsafe_allow_html=True)
            seguro_borrar_anmat = st.checkbox("Confirmar envío a papelera", key="chk_anmat")
        with col_del3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Enviar a Papelera", key="btn_del_anmat", disabled=(id_eliminar_anmat == "-" or not seguro_borrar_anmat)):
                try:
                    conn_del_a = sqlite3.connect(DB_PATH)
                    conn_del_a.execute("PRAGMA foreign_keys = ON")
                    cur_del_a = conn_del_a.cursor()
                    # Borrado Lógico: Update estado a 'eliminado'
                    cur_del_a.execute("UPDATE alerta_anmat SET estado = 'eliminado' WHERE id_alerta = ?", (id_eliminar_anmat,))
                    conn_del_a.commit()
                    if cur_del_a.rowcount > 0:
                        st.success(f"✅ Alerta {id_eliminar_anmat} enviada a papelera. (Presiona F5)")
                    else:
                        st.warning("El ID no existía.")
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
                finally:
                    conn_del_a.close()
                    
        # --- EDITAR ANMAT ---
        st.divider()
        st.markdown("### ✏️ Editar Alerta ANMAT Existente")
        id_editar_anmat = st.selectbox("Selecciona el ID a editar:", options=opciones_id_anmat, key="edit_anmat_sel")
        
        if id_editar_anmat != "-":
            alerta_actual = df_anmat[df_anmat['ID'] == int(id_editar_anmat)].iloc[0]
            
            with st.form("form_editar_anmat"):
                st.info(f"Modificando alerta: **{alerta_actual['Producto']}**")
                
                upd_producto = st.text_input("Producto:", value=alerta_actual['Producto'])
                col_upd1, col_upd2 = st.columns(2)
                with col_upd1:
                    upd_lote = st.text_input("Lote:", value=alerta_actual['Lote'])
                with col_upd2:
                    upd_venc = st.text_input("Vencimiento:", value=alerta_actual['Vencimiento'])
                
                upd_motivo = st.text_input("Motivo:", value=alerta_actual['Motivo'])    
                upd_accion = st.text_area("Acción Requerida:", value=alerta_actual['Acción Requerida'])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    if upd_producto.strip() == "" or upd_accion.strip() == "" or upd_motivo.strip() == "":
                        st.error("Producto, Motivo y Acción Requerida son obligatorios.")
                    else:
                        try:
                            conn_upd_a = sqlite3.connect(DB_PATH)
                            conn_upd_a.execute("PRAGMA foreign_keys = ON")
                            cur_upd_a = conn_upd_a.cursor()
                            cur_upd_a.execute("""
                                UPDATE alerta_anmat 
                                SET producto = ?, lote = ?, vencimiento = ?, motivo = ?, accion_requerida = ?
                                WHERE id_alerta = ?
                            """, (upd_producto, upd_lote, upd_venc, upd_motivo, upd_accion, id_editar_anmat))
                            conn_upd_a.commit()
                            if cur_upd_a.rowcount > 0:
                                st.success(f"✅ Alerta {id_editar_anmat} actualizada exitosamente. (Presiona F5)")
                        except Exception as e:
                            st.error(f"Error: {e}")
                        finally:
                            conn_upd_a.close()

    # --- PAPELERA DE RECICLAJE ANMAT ---
    st.divider()
    with st.expander("♻️ Abrir Papelera de Reciclaje (ANMAT)", expanded=False):
        df_papelera_anmat = pd.read_sql_query("""
            SELECT id_alerta AS 'ID', producto AS 'Producto', motivo AS 'Motivo'
            FROM alerta_anmat
            WHERE estado = 'eliminado'
        """, conn_anmat)
        
        if df_papelera_anmat.empty:
            st.info("La papelera de ANMAT está vacía.")
        else:
            st.table(df_papelera_anmat)
            op_restaurar_anmat = ["-"] + df_papelera_anmat['ID'].astype(str).tolist()
            col_ra1, col_ra2 = st.columns([2, 2])
            with col_ra1:
                id_restaurar_anmat = st.selectbox("ID a Restaurar:", options=op_restaurar_anmat, key="sel_rest_anmat")
            with col_ra2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("♻️ Restaurar Alerta (a Activo)", key="btn_rest_anmat", disabled=(id_restaurar_anmat == "-")):
                    try:
                        conn_res_a = sqlite3.connect(DB_PATH)
                        cur_res_a = conn_res_a.cursor()
                        cur_res_a.execute("UPDATE alerta_anmat SET estado = 'activo' WHERE id_alerta = ?", (id_restaurar_anmat,))
                        conn_res_a.commit()
                        st.success(f"✅ Alerta {id_restaurar_anmat} restaurada. (Presiona F5)")
                    except Exception as e:
                        st.error(f"Error al restaurar: {e}")
                    finally:
                        conn_res_a.close()

    conn_anmat.close()

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
        # Modificado para que el simulador ignore los eliminados
        cursor_sim.execute("""
            SELECT b.tipo_alerta, b.mensaje, b.fecha_vigencia, b.estado, m.nombre_droga 
            FROM boletin_os b
            JOIN obra_social o ON b.id_obra_social = o.id_obra_social
            LEFT JOIN medicamento m ON b.id_medicamento = m.id_medicamento
            WHERE o.nombre_os = ? 
              AND (m.nombre_droga = ? OR b.id_medicamento IS NULL)
              AND b.estado != 'eliminado'
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

#para abrirlo: python -m streamlit run panel_local.py