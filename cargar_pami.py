import pandas as pd
import sqlite3

print("⏳ Procesando Nuevo Vademécum Oficial de PAMI...")

# 1. Cargamos el nuevo Excel
archivo_excel = 'vademecum_pami.xlsx'
df_pami = pd.read_excel(archivo_excel)

# Limpiamos los nombres de las columnas
df_pami.columns = df_pami.columns.str.strip().str.upper()

# 2. Funciones de limpieza de datos
def limpiar_porcentaje(valor):
    try:
        return int(str(valor).replace('%', '').strip())
    except:
        return 0

def limpiar_moneda(valor):
    try:
        return float(str(valor).replace('$', '').replace(',', '').strip())
    except:
        return 0.0

# Aplicamos la limpieza a las columnas correspondientes
df_pami['cobertura_num'] = df_pami['COBERTURA'].apply(limpiar_porcentaje)
df_pami['copago_num'] = df_pami['COPAGO'].apply(limpiar_moneda)

# 3. Conexión a Base de Datos
conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'PAMI'")
id_pami = cursor.fetchone()[0]

print("🧹 Limpiando registros anteriores de PAMI...")
cursor.execute("DELETE FROM regla_validacion WHERE id_obra_social = ?", (id_pami,))

reglas_insertadas = 0
print("📥 Insertando catálogo PAMI con detalles comerciales. Esto puede tardar...")

# 4. Iteramos y mapeamos al esquema centralizado
for index, row in df_pami.iterrows():
    droga_pami = str(row.get('DROGA', '')).strip().lower()
    
    if not droga_pami or droga_pami == 'nan':
        continue

    cursor.execute("SELECT id_medicamento FROM medicamento WHERE LOWER(nombre_droga) = ?", (droga_pami,))
    resultado = cursor.fetchone()
    if resultado:
        id_med = resultado[0]
    else:
        cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (droga_pami.capitalize(),))
        id_med = cursor.lastrowid

    presentacion = str(row.get('PRESENTACION', '-'))
    marca = str(row.get('MARCA', '-'))
    laboratorio = str(row.get('LABORATORIO', '-'))
    copago = row['copago_num']
    porcentaje = row['cobertura_num']
    
    # PAMI no incluye Monto OS ni PVP en este reporte, usamos 0
    precio_venta = 0.0 
    monto_cobertura = 0.0

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

print(f"✅ ¡Éxito total! Se insertaron {reglas_insertadas} presentaciones detalladas de PAMI.")