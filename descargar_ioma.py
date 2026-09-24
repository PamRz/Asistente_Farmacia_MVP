import requests

url = "https://sistemas.ioma.gba.gov.ar/vademecum/Home/GetJsonList"

# Simulamos ser tu navegador Firefox con los encabezados que capturaste
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://sistemas.ioma.gba.gov.ar/vademecum/"
}

print("Descargando el Vademécum completo de IOMA... Esto puede tardar unos segundos.")

try:
    # Hacemos la petición al servidor
    respuesta = requests.get(url, headers=headers)
    respuesta.raise_for_status() # Verificamos que no haya errores
    
    # Guardamos el texto crudo en un archivo JSON
    with open("ioma_datos.json", "w", encoding="utf-8") as archivo:
        archivo.write(respuesta.text)
        
    print("✅ ¡Éxito! El archivo 'ioma_datos.json' se ha guardado en tu carpeta.")

except Exception as e:
    print(f"❌ Ocurrió un error: {e}")