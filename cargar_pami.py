import pandas as pd
import sqlite3

print("Leyendo el archivo Excel (esto puede demorar unos segundos)...")
df = pd.read_excel('vademecum_pami.xlsx')

# Extraemos solo los nombres de las drogas sin repetir
drogas_unicas = df['DROGA'].dropna().unique()
print(f"Se encontraron {len(drogas_unicas)} drogas únicas. Conectando a la base de datos...")

# Nos conectamos a tu base local
conn = sqlite3.connect('asistente_farmacia.db')
cursor = conn.cursor()

agregados = 0
for droga in drogas_unicas:
    # Verificamos si la droga ya existe para no duplicar lo que cargaste a mano
    cursor.execute("SELECT id_medicamento FROM medicamento WHERE nombre_droga = ?", (droga,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO medicamento (nombre_droga) VALUES (?)", (droga,))
        agregados += 1

conn.commit()
conn.close()
print(f"¡Carga exitosa! Se agregaron {agregados} medicamentos nuevos al catálogo.")