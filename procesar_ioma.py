import json
import pandas as pd
import sqlite3

print("⏳ Procesando Vademécum de IOMA...")

# 1. Cargamos el JSON
with open('ioma_datos.json', 'r', encoding='utf-8') as f:
    datos_crudos = json.load(f)

lista_datos = datos_crudos.get('data', datos_crudos)
df_ioma = pd.DataFrame(lista_datos)
df_ioma.columns = df_ioma.columns.str.lower()

# 2. Función de limpieza extrema para la columna 'nueva_cobertura'
def extraer_porcentaje(valor):
    try:
        # Quitamos espacios y el símbolo de porcentaje si existe
        val_str = str(valor).replace('%', '').strip()
        num = float(val_str)
        
        # Escudo de seguridad: La cobertura nunca puede ser mayor al 100%
        if num > 100:
            num = 100
            
        return int(num)
    except:
        return 0

# Aplicamos la función a la columna oficial de IOMA
df_ioma['cobertura_real'] = df_ioma['nueva_cobertura'].apply(extraer_porcentaje)

# Agrupamos por principio activo sacando el porcentaje MÁXIMO
df_agrupado = df_ioma.groupby('principio_activo')['cobertura_real'].max().reset_index()

# 3. Actualización de la Base de Datos
conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

# Obtenemos el ID de IOMA
cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'IOMA'")
id_ioma = cursor.fetchone()[0]

print("🧹 Limpiando base de datos...")
cursor.execute("DELETE FROM regla_validacion WHERE id_obra_social = ?", (id_ioma,))

drogas_procesadas = 0
reglas_insertadas = 0

print("📥 Insertando normativas validadas...")
for index, row in df_agrupado.iterrows():
    nombre_droga = str(row['principio_activo']).strip().lower()
    cobertura_max = row['cobertura_real']
    
    # Ignoramos campos vacíos o con cobertura 0
    if not nombre_droga or nombre_droga == 'nan' or cobertura_max == 0:
        continue

    # Buscamos o creamos el medicamento
    cursor.execute("SELECT id_medicamento FROM medicamento WHERE LOWER(nombre_droga) = ?", (nombre_droga,))
    resultado = cursor.fetchone()
    
    if resultado:
        id_med = resultado[0]
    else:
        cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (nombre_droga.capitalize(),))
        id_med = cursor.lastrowid
        drogas_procesadas += 1

    # Insertamos la regla con la FECHA ACTUAL automatizada
    observacion = f"Cobertura variable (hasta {cobertura_max}% según presentación). Verificar validación online."
    
    cursor.execute("""
        INSERT INTO regla_validacion 
        (id_obra_social, id_medicamento, cobertura_porcentaje, requiere_token, tope_envases, requisito_observacion, fecha_carga) 
        VALUES (?, ?, ?, 'NO', 2, ?, datetime('now', 'localtime'))
    """, (id_ioma, id_med, cobertura_max, observacion))
    reglas_insertadas += 1

conn.commit()
conn.close()

print(f"✅ ¡Éxito! Se insertaron {reglas_insertadas} normativas limpias y validadas.")