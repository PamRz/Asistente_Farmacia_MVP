import pandas as pd
import sqlite3

print("⏳ Procesando Vademécum Detallado de PAMI...")

# 1. Cargamos el Excel (cambia el nombre si tu archivo se llama distinto)
# Si te da error de lectura, asegúrate de haber corrido: pip install openpyxl
archivo_excel = 'vademecum_pami.xlsx' 
df_pami = pd.read_excel(archivo_excel)

# Limpiamos nombres de columnas quitando espacios extra
df_pami.columns = df_pami.columns.str.strip().str.upper()

# 2. Conectamos a la Base de Datos
conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

# Obtenemos el ID de PAMI
cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'PAMI'")
resultado_os = cursor.fetchone()

if not resultado_os:
    print("❌ PAMI no existe en la base de datos. Creándolo...")
    cursor.execute("INSERT INTO obra_social (nombre_os) VALUES ('PAMI')")
    id_pami = cursor.lastrowid
else:
    id_pami = resultado_os[0]

print("🧹 Limpiando registros anteriores de PAMI...")
cursor.execute("DELETE FROM regla_validacion WHERE id_obra_social = ?", (id_pami,))

reglas_insertadas = 0

print("📥 Insertando catálogo PAMI por presentación. Esto puede tardar...")

# 3. Iteramos sobre el Excel traduciendo las columnas de PAMI a nuestro sistema
for index, row in df_pami.iterrows():
    # En PAMI la droga está en la columna 'DROGA'
    droga_pami = str(row.get('DROGA', '')).strip().lower()
    
    # Arreglamos errores de codificación del Excel de PAMI (ej: acetilciste¡na -> acetilcisteina)
    droga_pami = droga_pami.replace('¡', 'i')
    
    if not droga_pami or droga_pami == 'nan':
        continue

    # Buscamos o insertamos la droga genérica
    cursor.execute("SELECT id_medicamento FROM medicamento WHERE LOWER(nombre_droga) = ?", (droga_pami,))
    resultado = cursor.fetchone()
    if resultado:
        id_med = resultado[0]
    else:
        cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (droga_pami.capitalize(),))
        id_med = cursor.lastrowid

    # Extraemos los datos mapeando las columnas de PAMI
    presentacion = str(row.get('PRESENTA', '-'))
    marca = str(row.get('NOMBRE', '-'))
    
    # Si la celda está vacía, ponemos 0
    try:
        monto_cobertura = float(row.get('PLAN PASIVO ANEXO2', 0))
    except:
        monto_cobertura = 0.0

    # PAMI no suele poner Laboratorio ni PVP en este anexo, los dejamos genéricos
    laboratorio = "-"
    precio_venta = 0.0
    copago = 0.0
    porcentaje = 100 if monto_cobertura > 0 else 0 # Asumimos 100% de cobertura sobre su anexo
    
    # Insertamos
    cursor.execute("""
        INSERT INTO regla_validacion 
        (id_obra_social, id_medicamento, cobertura_porcentaje, requiere_token, tope_envases, 
         requisito_observacion, fecha_carga, presentacion, marca_comercial, precio_venta, 
         monto_cobertura, copago, laboratorio) 
        VALUES (?, ?, ?, 'NO', 2, 'Verificar receta electrónica de PAMI', datetime('now', 'localtime'), 
                ?, ?, ?, ?, ?, ?)
    """, (id_pami, id_med, porcentaje, presentacion, marca, precio_venta, monto_cobertura, copago, laboratorio))
    reglas_insertadas += 1

conn.commit()
conn.close()

print(f"✅ ¡Éxito total! Se insertaron {reglas_insertadas} presentaciones de PAMI.")