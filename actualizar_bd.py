import sqlite3

conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

try:
    # 1. Agregamos la columna como texto vacío (permitido por SQLite)
    cursor.execute("ALTER TABLE regla_validacion ADD COLUMN fecha_carga TEXT;")
    
    # 2. Actualizamos todos los registros existentes inyectando la fecha y hora actual local
    cursor.execute("UPDATE regla_validacion SET fecha_carga = datetime('now', 'localtime');")
    
    conn.commit()
    print("✅ Columna 'fecha_carga' agregada y todos los registros actualizados con éxito.")
except sqlite3.OperationalError as e:
    print(f"Aviso: {e}")

conn.close()