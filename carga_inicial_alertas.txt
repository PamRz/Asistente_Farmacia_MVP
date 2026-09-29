import sqlite3

def cargar_lote_inicial():
    conn = sqlite3.connect('asistente_farmacia.db')
    cursor = conn.cursor()

    try:
        # ==========================================
        # 1. CARGA DE ALERTAS ANMAT (Corregido con campo 'motivo')
        # ==========================================
        alertas_anmat = [
            ('Fentanilo + Marca: HLB Pharma (Inyectable 0,05 mg/ml)', '31202', 'SEP-26', 'Desvío de calidad', '🔴 CRÍTICO: NO DISPENSAR y aislar stock.'),
            ('Accesorio: Accu-Chek Guide 50 Tiras', '105938', 'N/A', 'Producto falsificado', '🔴 CRÍTICO: NO DISPENSAR, separar stock y reportar a RPVF.')
        ]
        
        cursor.executemany("""
            INSERT INTO alerta_anmat (producto, lote, vencimiento, motivo, accion_requerida) 
            VALUES (?, ?, ?, ?, ?)
        """, alertas_anmat)
        print("✅ Alertas ANMAT insertadas.")

        # ==========================================
        # 2. OBTENER IDs DE REFERENCIA
        # ==========================================
        cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os LIKE '%IOMA%'")
        res_ioma = cursor.fetchone()
        if not res_ioma:
            raise Exception("No se encontró la obra social IOMA en la base de datos.")
        id_ioma = res_ioma[0]

        cursor.execute("SELECT id_medicamento FROM medicamento WHERE nombre_droga LIKE '%anticonceptivo%' LIMIT 1")
        res_anti = cursor.fetchone()
        id_anticonceptivo = res_anti[0] if res_anti else None

        if not id_anticonceptivo:
            print("⚠️ Nota: No se encontró 'Anticonceptivos' en la tabla de medicamentos. La alerta se cargará como general.")

        # ==========================================
        # 3. CARGA DE BOLETINES IOMA (Generales y Específicos)
        # ==========================================
        boletines_ioma = [
            (id_ioma, 'critica', 'NO DISPENSAR. Desde el 01/07/2026 el formato Receta UMA / Telemedicina no tiene validez para facturación.', 'activo', None),
            (id_ioma, 'advertencia', 'Plan Mayor Cobertura: La receta/autorización impresa debe tener sello y firma ORIGINAL del médico.', 'activo', None),
            (id_ioma, 'informativa', 'Validar con nueva identificación: 9 dígitos (1 Sexo + 8 DNI). Excepción: Afiliados extraña jurisdicción (credencial "X").', 'activo', None),
            (id_ioma, 'informativa', 'Receta Electrónica Oficial: No requiere copia impresa de la receta. Liquidar presentando ticket/comprobante de validación.', 'activo', None),
            (id_ioma, 'informativa', 'Plan Crónicos: Recetario VÁLIDO para dispensa de anticonceptivos, aunque el diagnóstico no figure en el listado de patologías.', 'activo', id_anticonceptivo)
        ]

        cursor.executemany("""
            INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia, estado, id_medicamento) 
            VALUES (?, ?, ?, date('now', 'localtime'), ?, ?)
        """, boletines_ioma)
        
        print("✅ Boletines de IOMA insertados correctamente.")

        conn.commit()
        print("🚀 Carga inicial completada con éxito.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error durante la carga: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cargar_lote_inicial()