import sqlite3

conexion = sqlite3.connect('asistente_farmacia.db')
cursor = conexion.cursor()

try:
    # 1. Obtenemos los IDs reales de las obras sociales
    cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'IOMA'")
    resultado_ioma = cursor.fetchone()
    id_ioma = resultado_ioma[0] if resultado_ioma else None

    cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'PAMI'")
    resultado_pami = cursor.fetchone()
    id_pami = resultado_pami[0] if resultado_pami else None

    # Limpiamos la tabla por si se llega a ejecutar este script más de una vez
    cursor.execute("DELETE FROM boletin_os")

    boletines_insertados = 0

    # 2. Insertamos el boletín de IOMA
    if id_ioma:
        cursor.execute("""
            INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia)
            VALUES (?, 'informativa', 'Atención mostrador: Recuerde verificar que el primer dígito del número de afiliado coincida con el sexo registrado en el DNI, según normativa vigente.', '2026-09-27')
        """, (id_ioma,))
        boletines_insertados += 1

    # 3. Insertamos el boletín de PAMI
    if id_pami:
        cursor.execute("""
            INSERT INTO boletin_os (id_obra_social, tipo_alerta, mensaje, fecha_vigencia)
            VALUES (?, 'critica', 'Rechazo de facturación: Ya no se aceptan recetas físicas tradicionales. Solo es válida la receta electrónica oficial escaneada en el sistema.', '2026-09-27')
        """, (id_pami,))
        boletines_insertados += 1
    # 4. Confirmamos los cambios y cerramos la conexión

    conexion.commit()
    print(f"✅ ¡Listo! Se insertaron {boletines_insertados} boletines de prueba en la base de datos.")

except Exception as e:
    print(f"❌ Ocurrió un error: {e}")

finally:
    conexion.close()