
# Este script actualiza la columna 'fecha_carga' de la tabla 'regla_validacion' en la base de datos 'asistente_farmacia.db' para que todos los registros adopten la fecha y hora local actual. Esto es útil para mantener un registro actualizado de cuándo se cargaron los datos, especialmente después de agregar nuevos registros, como los 457 de IOMA.

import sqlite3

conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

try:
    # Esta línea fuerza a que TODOS los registros (incluyendo los 457 nuevos de IOMA) adopten la fecha local actual
    cursor.execute("UPDATE regla_validacion SET fecha_carga = datetime('now', 'localtime');")
    
    conn.commit()
    print("✅ Todas las fechas de carga han sido actualizadas con éxito.")
except sqlite3.OperationalError as e:
    print(f"❌ Error: {e}")

conn.close()