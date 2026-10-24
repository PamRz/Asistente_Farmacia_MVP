💊 FarmaCheck

Prototipo web para la consulta de normativas de dispensación farmacéutica y alertas sanitarias.

FarmaCheck (inicialmente concebido como "El Asistente de Farmacia") es una aplicación desarrollada para agilizar el trabajo en el mostrador de la farmacia. Centraliza información estructurada sobre normativas de coberturas (IOMA, PAMI), topes de envases, requisitos de auditoría y alertas sanitarias (ANMAT), reduciendo el tiempo de búsqueda y el riesgo de errores por información desactualizada.

Este proyecto fue desarrollado como trabajo final para el Taller Integrador de la Tecnicatura Universitaria en Informática (UNNE).
✨ Características Principales

    Buscador Rápido: Consulta de coberturas filtrando por Obra Social y Principio Activo/Medicamento en menos de 15 segundos.

    Divulgación Progresiva: Interfaz en dos columnas que separa las alertas transversales de las normativas específicas de cada droga.

    Alertas Sanitarias (ANMAT): Visualización de disposiciones, retiros de mercado y lotes observados.

    Administración Local Segura: Un entorno back-office aislado para realizar operaciones CRUD (Crear, Leer, Actualizar, Borrado Lógico y Restauración de papelera) sin exponer la base de datos pública.

    Procesamiento ETL Automatizado: Scripts en Python (utilizando pandas) para la ingesta, limpieza y normalización masiva de vademécums y boletines desde archivos Excel y JSON.

🛠️ Tecnologías Utilizadas

    Lenguaje: Python 3

    Front-end / Interfaz Web: Streamlit

    Base de Datos: SQLite3 (Relacional, motor autocontenido)

    Análisis de Datos (ETL): Pandas, NumPy

    Despliegue: Streamlit Community Cloud / GitHub

🏗️ Arquitectura del Sistema

El proyecto utiliza una arquitectura híbrida para garantizar la integridad de los datos:

    Front-Office (Público): Aplicación web de solo lectura desplegada en la nube para el personal de mostrador.

    Back-Office (Local): Herramienta de gestión (panel_local.py) ejecutada de manera local por el Administrador de Datos para editar la base SQLite. Los cambios aprobados se versionan vía Git y se publican mediante commits.

🚀 Instalación y Uso Local

Para ejecutar el entorno de administración local en tu máquina:

    Clonar el repositorio:
    Bash

    git clone https://github.com/tu-usuario/tu-repositorio.git
    cd tu-repositorio

    Instalar las dependencias necesarias:
    Bash

    pip install pandas numpy streamlit

    Iniciar el Panel de Administración Local:
    Bash

    python -m streamlit run panel_local.py

📂 Estructura del Proyecto

    app.py: Aplicación web principal (Front-end público).

    panel_local.py: Interfaz de administración (Back-office local).

    asistente_farmacia.db: Base de datos SQLite principal.

    procesar_ioma.py / cruzar_pami.py: Scripts ETL para limpieza y normalización de datos.

    vademecum_pami.xlsx / ioma_datos.json: Archivos crudos de ejemplo para la ingesta de datos.

⚠️ Aviso Legal

FarmaCheck es una herramienta de apoyo preventivo y consulta rápida basada en boletines oficiales. No reemplaza a los validadores transaccionales oficiales de las Obras Sociales. La validación final en el sistema oficial y la dispensa física son responsabilidad exclusiva del profesional farmacéutico de mostrador.

Desarrollado por: Pamela Romina Ramírez
