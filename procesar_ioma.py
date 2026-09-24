import json
import pandas as pd
import sqlite3
import numpy as np

print("⏳ Analizando y recalculando el Vademécum de IOMA...")

# 1. Cargamos el JSON
with open('ioma_datos.json', 'r', encoding='utf-8') as f:
    datos_crudos = json.load(f)

lista_datos = datos_crudos.get('data', datos_crudos)
df_ioma = pd.DataFrame(lista_datos)
df_ioma.columns = df_ioma.columns.str.lower()

# 2. Conversión segura de precios (por si vienen con comas en vez de puntos)
def limpiar_numero(valor):
    try:
        # Convertimos a string, cambiamos comas por puntos y quitamos símbolos raros
        val_str = str(valor).replace('$', '').replace('.', '').replace(',', '.')
        return float(val_str)
    except:
        return 0.0

df_ioma['precio_venta_num'] = df_ioma['precio_venta'].apply(limpiar_numero)
df_ioma['monto_ioma_num'] = df_ioma['nuevo_monto_ioma'].apply(limpiar_numero)

# 3. EL CÁLCULO MÁGICO: (Monto IOMA / Precio Venta) * 100
# Usamos np.where para evitar dividir por cero
df_ioma['cobertura_calculada'] = np.where(
    df_ioma['precio_venta_num'] > 0, 
    (df_ioma['monto_ioma_num'] / df_ioma['precio_venta_num']) * 100, 
    0
)

# Redondeamos al número entero más cercano
df_ioma['cobertura_real'] = df_ioma['cobertura_calculada'].round().astype(int)

# Agrupamos por principio activo sacando el porcentaje MÁXIMO real
df_agrupado = df_ioma.groupby('principio_activo')['cobertura_real'].max().reset_index()

# 4. Actualización Quirúrgica de la Base de Datos
conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

# Obtenemos el ID de IOMA
cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'IOMA'")
id_ioma = cursor.fetchone()[0]

print("🧹 Limpiando registros anteriores de IOMA para evitar duplicados...")
cursor.execute("DELETE FROM regla_validacion WHERE id_obra_social = ?", (id_ioma,))

drogas_procesadas = 0
reglas_insertadas = 0

print("📥 Insertando datos recalculados con fecha de actualización...")
for index, row in df_agrupado.iterrows():
    nombre_droga = str(row['principio_activo']).strip().lower()
    cobertura_max = row['cobertura_real']
    
    if not nombre_droga or nombre_droga == 'nan' or cobertura_max == 0:
        continue # Saltamos errores o drogas sin cobertura real

    # Aseguramos que la droga exista
    cursor.execute("SELECT id_medicamento FROM medicamento WHERE LOWER(nombre_droga) = ?", (nombre_droga,))
    resultado = cursor.fetchone()
    
    if resultado:
        id_med = resultado[0]
    else:
        cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (nombre_droga.capitalize(),))
        id_med = cursor.lastrowid
        drogas_procesadas += 1

    # Insertamos la regla con LA FECHA ACTUAL incluida (datetime('now', 'localtime'))
    observacion = f"Cobertura variable (hasta {cobertura_max}% según presentación). Verificar en portal oficial para el producto específico."
    
    cursor.execute("""
        INSERT INTO regla_validacion 
        (id_obra_social, id_medicamento, cobertura_porcentaje, requiere_token, tope_envases, requisito_observacion, fecha_carga) 
        VALUES (?, ?, ?, 'NO', 2, ?, datetime('now', 'localtime'))
    """, (id_ioma, id_med, cobertura_max, observacion))
    reglas_insertadas += 1

conn.commit()
conn.close()

print(f"✅ ¡Éxito total! Se recalculó toda la base. {reglas_insertadas} normativas de IOMA insertadas correctamente con sus fechas de carga.")