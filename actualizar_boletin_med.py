import sqlite3

conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

try:
    # Agregamos la columna 'id_medicamento', permitiendo que quede vacía (NULL) para alertas generales
    cursor.execute("ALTER TABLE boletin_os ADD COLUMN id_medicamento INTEGER DEFAULT NULL")
    conn.commit()
    print("✅ Columna 'id_medicamento' agregada exitosamente a la base de datos.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Atención: {e} (Probablemente la columna ya existe).")

conn.close()