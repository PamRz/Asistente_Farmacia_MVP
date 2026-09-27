import sqlite3

print("⏳ Conectando a la base de datos...")
conexion = sqlite3.connect('asistente_farmacia.db')
cursor = conexion.cursor()

nuevas_columnas = [
    ("presentacion", "TEXT"),
    ("marca_comercial", "TEXT"),
    ("precio_venta", "REAL"),
    ("monto_cobertura", "REAL"),
    ("copago", "REAL"),
    ("laboratorio", "TEXT")
]

columnas_agregadas = 0

for columna, tipo in nuevas_columnas:
    try:
        # Intentamos agregar la columna
        cursor.execute(f"ALTER TABLE regla_validacion ADD COLUMN {columna} {tipo}")
        columnas_agregadas += 1
        print(f"✅ Columna '{columna}' agregada exitosamente.")
    except sqlite3.OperationalError as e:
        # Si la columna ya existe, SQLite arrojará un error. Lo capturamos para que el script no se rompa.
        if "duplicate column name" in str(e).lower():
            print(f"⚠️ La columna '{columna}' ya existía. Saltando...")
        else:
            print(f"❌ Error al agregar '{columna}': {e}")

conexion.commit()
conexion.close()

print(f"\n🎉 Proceso finalizado. Se agregaron {columnas_agregadas} columnas nuevas a la estructura.")