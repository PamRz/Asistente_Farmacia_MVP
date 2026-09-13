import pandas as pd
import sqlite3

print("Procesando las coberturas de PAMI...")
df = pd.read_excel('vademecum_pami.xlsx')

# Limpiamos el símbolo '%' y convertimos la columna a números enteros. 
# Si una droga tiene varias presentaciones, tomamos la cobertura máxima para el MVP.
df['cobertura_num'] = df['COBERTURA'].astype(str).str.replace('%', '').astype(int)
reglas_pami = df.groupby('DROGA')['cobertura_num'].max().reset_index()

conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

agregadas = 0
for index, row in reglas_pami.iterrows():
    droga = row['DROGA']
    cobertura = row['cobertura_num']
    
    # Buscamos el ID que SQLite le asignó a este medicamento en el paso anterior
    cursor.execute("SELECT id_medicamento FROM medicamento WHERE nombre_droga = ?", (droga,))
    resultado = cursor.fetchone()
    
    if resultado:
        id_med = resultado[0]
        # Verificamos que la regla no exista ya para no generar duplicados
        cursor.execute("SELECT id_regla FROM regla_validacion WHERE id_obra_social = 1 AND id_medicamento = ?", (id_med,))
        if not cursor.fetchone():
            # Insertamos la normativa estableciendo PAMI (ID 1), el tope referencial y el porcentaje
            cursor.execute("""
                INSERT INTO regla_validacion 
                (id_obra_social, id_medicamento, cobertura_porcentaje, requiere_token, tope_envases, requisito_observacion) 
                VALUES (1, ?, ?, 'NO', 2, 'Carga masiva automatizada Vademécum PAMI')
            """, (id_med, int(cobertura)))
            agregadas += 1

conn.commit()
conn.close()
print(f"¡Listo! Se vincularon {agregadas} reglas de cobertura en la tabla transaccional.")