import sqlite3

# Establecemos la conexión a la base de datos SQLite
conexion = sqlite3.connect('asistente_farmacia.db')
cursor = conexion.cursor()

try:
    # Ejecutamos la creación de la tabla asegurándonos de que no exista previamente
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS boletin_os (
        id_boletin INTEGER PRIMARY KEY AUTOINCREMENT,
        id_obra_social INTEGER,
        tipo_alerta TEXT,
        mensaje TEXT,
        fecha_vigencia DATETIME,
        FOREIGN KEY(id_obra_social) REFERENCES obra_social(id_obra_social)
    );
    """)
    # Confirmamos los cambios
    conexion.commit()
    print("✅ La tabla 'boletin_os' se ha creado exitosamente en la base de datos.")
# Manejamos posibles errores
except sqlite3.OperationalError as e:
    print(f"❌ Error al crear la tabla: {e}")

finally:
    conexion.close()