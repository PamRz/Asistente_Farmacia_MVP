import json
import pandas as pd
import sqlite3
import numpy as np

print("⏳ Procesando Vademécum Detallado de IOMA...")

# 1. Cargamos el JSON
with open('ioma_datos.json', 'r', encoding='utf-8') as f:
    datos_crudos = json.load(f)

lista_datos = datos_crudos.get('data', datos_crudos)
df_ioma = pd.DataFrame(lista_datos)
df_ioma.columns = df_ioma.columns.str.lower()

# 2. Limpieza de números (precios y montos)
def limpiar_numero(valor):
    try:
        val_str = str(valor).replace('$', '').strip()
        if '.' in val_str and ',' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        return float(val_str)
    except:
        return 0.0

# Usamos .get() por si el JSON cambia levemente los nombres de las columnas
df_ioma['precio_venta_num'] = df_ioma.get('precio_venta', pd.Series([0]*len(df_ioma))).apply(limpiar_numero)
df_ioma['monto_ioma_num'] = df_ioma.get('nuevo_monto_ioma', pd.Series([0]*len(df_ioma))).apply(limpiar_numero)

# 3. Cálculos comerciales
# Calculamos el copago (Precio total menos lo que cubre IOMA)
df_ioma['copago_calculado'] = df_ioma['precio_venta_num'] - df_ioma['monto_ioma_num']
# Si por error matemático da negativo, lo dejamos en 0
df_ioma['copago_calculado'] = np.where(df_ioma['copago_calculado'] < 0, 0, df_ioma['copago_calculado'])

# Calculamos el porcentaje real
df_ioma['cobertura_porcentaje'] = np.where(
    df_ioma['precio_venta_num'] > 0, 
    (df_ioma['monto_ioma_num'] / df_ioma['precio_venta_num']) * 100, 
    0
)
df_ioma['cobertura_porcentaje'] = np.where(df_ioma['cobertura_porcentaje'] > 100, 100, df_ioma['cobertura_porcentaje'])
df_ioma['cobertura_porcentaje'] = df_ioma['cobertura_porcentaje'].round().astype(int)

# 4. Actualización de la Base de Datos
conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'IOMA'")
id_ioma = cursor.fetchone()[0]

print("🧹 Limpiando registros anteriores de IOMA...")
cursor.execute("DELETE FROM regla_validacion WHERE id_obra_social = ?", (id_ioma,))

reglas_insertadas = 0

print("📥 Insertando catálogo completo por presentación. Esto puede tardar unos segundos...")
# ATENCIÓN: Ya no usamos groupby(), iteramos sobre TODAS las filas
for index, row in df_ioma.iterrows():
    nombre_droga = str(row.get('principio_activo', '')).strip().lower()
    
    # Filtramos filas vacías o sin precio
    if not nombre_droga or nombre_droga == 'nan' or row['precio_venta_num'] == 0:
        continue 

    # 1. Buscamos o insertamos la droga genérica
    cursor.execute("SELECT id_medicamento FROM medicamento WHERE LOWER(nombre_droga) = ?", (nombre_droga,))
    resultado = cursor.fetchone()
    if resultado:
        id_med = resultado[0]
    else:
        cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (nombre_droga.capitalize(),))
        id_med = cursor.lastrowid

    # 2. Extraemos los datos comerciales de la fila
    presentacion = str(row.get('presentacion', '-'))
    marca = str(row.get('producto', '-')) # En el JSON oficial suele llamarse 'producto'
    laboratorio = str(row.get('laboratorio', '-'))
    precio = row['precio_venta_num']
    monto_ioma = row['monto_ioma_num']
    copago = row['copago_calculado']
    porcentaje = row['cobertura_porcentaje']
    
    # 3. Insertamos el registro detallado
    cursor.execute("""
        INSERT INTO regla_validacion 
        (id_obra_social, id_medicamento, cobertura_porcentaje, requiere_token, tope_envases, 
         requisito_observacion, fecha_carga, presentacion, marca_comercial, precio_venta, 
         monto_cobertura, copago, laboratorio) 
        VALUES (?, ?, ?, 'NO', 2, 'Validación online obligatoria', datetime('now', 'localtime'), 
                ?, ?, ?, ?, ?, ?)
    """, (id_ioma, id_med, porcentaje, presentacion, marca, precio, monto_ioma, copago, laboratorio))
    reglas_insertadas += 1

conn.commit()
conn.close()

print(f"✅ ¡Éxito total! Se insertaron {reglas_insertadas} presentaciones comerciales en la base de datos.")