import json
import pandas as pd
import sqlite3

print("⏳ Procesando el Vademécum de IOMA...")

# 1. Abrimos el archivo JSON que acabas de descargar
with open('ioma_datos.json', 'r', encoding='utf-8') as f:
    datos_crudos = json.load(f)

lista_datos = datos_crudos.get('data', datos_crudos)
df_ioma = pd.DataFrame(lista_datos)

# Normalizamos las columnas a minúsculas para trabajar más fácil
df_ioma.columns = df_ioma.columns.str.lower()

# 2. Limpieza de datos (Actualizado a los nombres reales del JSON)
col_droga = 'principio_activo'  # Antes buscábamos 'droga'
col_cobertura = 'nueva_cobertura'  # Antes buscábamos 'cobertura'

if col_droga in df_ioma.columns and col_cobertura in df_ioma.columns:
    # Limpiamos el porcentaje si viene como texto
    df_ioma['cobertura_num'] = df_ioma[col_cobertura].astype(str).str.replace('%', '', regex=False).str.strip()
    df_ioma['cobertura_num'] = pd.to_numeric(df_ioma['cobertura_num'], errors='coerce').fillna(0).astype(int)

    # Agrupamos por principio activo y nos quedamos con el máximo porcentaje de cobertura
    df_agrupado = df_ioma.groupby(col_droga)['cobertura_num'].max().reset_index()

    # 3. Conexión a la base de datos local
    conn = sqlite3.connect('asistente_farmacia.db')
    cursor = conn.cursor()

    # Obtenemos el ID de la obra social IOMA
    cursor.execute("SELECT id_obra_social FROM obra_social WHERE nombre_os = 'IOMA'")
    id_ioma = cursor.fetchone()[0]

    drogas_nuevas = 0
    reglas_nuevas = 0

    # 4. Inserción masiva
    for index, row in df_agrupado.iterrows():
        nombre_droga = str(row[col_droga]).strip().lower()
        cobertura_max = row['cobertura_num']
        
        # Evitar drogas vacías
        if not nombre_droga or nombre_droga == 'nan':
            continue

        # Verificamos si la droga ya existe en el catálogo (ej: cargada previamente por PAMI)
        cursor.execute("SELECT id_medicamento FROM medicamento WHERE LOWER(nombre_droga) = ?", (nombre_droga,))
        resultado = cursor.fetchone()
        
        if resultado:
            id_med = resultado[0]
        else:
            # Si no existe, la agregamos
            cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (nombre_droga.capitalize(),))
            id_med = cursor.lastrowid
            drogas_nuevas += 1
            
        # Verificamos si ya existe la regla para evitar duplicados
        cursor.execute("SELECT id_regla FROM regla_validacion WHERE id_obra_social = ? AND id_medicamento = ?", (id_ioma, id_med))
        if not cursor.fetchone():
            observacion = f"Cobertura máxima registrada: {cobertura_max}%. Puede variar según marca y presentación. Consultar en portal oficial para el producto específico."
            cursor.execute("""
                INSERT INTO regla_validacion 
                (id_obra_social, id_medicamento, cobertura_porcentaje, requiere_token, tope_envases, requisito_observacion) 
                VALUES (?, ?, ?, 'NO', 2, ?)
            """, (id_ioma, id_med, cobertura_max, observacion))
            reglas_nuevas += 1

    conn.commit()
    conn.close()

    print(f"✅ ¡Base de datos actualizada! Se insertaron {drogas_nuevas} drogas nuevas y {reglas_nuevas} normativas de IOMA.")
else:
    print(f"❌ No se encontraron las columnas esperadas. Columnas del archivo: {df_ioma.columns.tolist()}")