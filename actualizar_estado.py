import sqlite3

conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

try:
    # Agregamos la columna 'estado' y por defecto ponemos todo lo existente como 'activo'
    cursor.execute("ALTER TABLE boletin_os ADD COLUMN estado TEXT DEFAULT 'activo'")
    conn.commit()
    print("✅ Columna 'estado' agregada exitosamente a la base de datos.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Atención: {e} (Probablemente la columna ya existe).")

conn.close()