# VERSIÓN MEJORADA DE STREAMLIT CLOUD. PARA TRABAJAR CON CASOS O CON EL ARCHIVO DE EXCEL COMPLETO. ÚLTIMA VERSIÓN.
import streamlit as st
import pandas as pd
import time
from io import BytesIO
import os
import google.generativeai as genai

# === CONFIGURACIÓN DE GEMINI ===
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key no configurada. Definila como variable de entorno GEMINI_API_KEY en Streamlit Cloud.")
    st.stop()

genai.configure(api_key=API_KEY)

# === FUNCIÓN DE CLASIFICACIÓN ===
def clasificar_queja_con_razon(texto):
    prompt = f"""Leé la siguiente queja de un pasajero y devolvé SOLO:

1. La categoría más adecuada según esta lista:
- Servicio Operativo y Frecuencia
- Infraestructura y Mantenimiento
- Seguridad y Control
- Atención al Usuario
- Otros
- Conducta de Terceros
- Incidentes y Emergencias
- Accesibilidad y Público Vulnerable
- Personal y Desempeño Laboral
- Ambiente y Confort
- Tarifas y Boletos

2. Una breve razón de por qué fue clasificada así.

Formato de salida:
Categoría: <nombre de categoría>
Razón: <explicación>

Texto: {texto}
"""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt,
            generation_config={
                "temperature": 0.2,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 256
            })
        respuesta = response.text.strip()

        categoria, razon = "", ""
        for linea in respuesta.splitlines():
            if linea.lower().startswith("categoría:") or linea.lower().startswith("categoria:"):
                categoria = linea.split(":", 1)[1].strip()
            elif linea.lower().startswith("razón:") or linea.lower().startswith("razon:"):
                razon = linea.split(":", 1)[1].strip()
        return categoria, razon

    except Exception as e:
        return "ERROR", str(e)

# === INTERFAZ STREAMLIT ===
st.set_page_config(page_title="Clasificador de Quejas", layout="centered")
st.title("🧾 Clasificador de Quejas de Pasajeros")

modo = st.radio("¿Qué querés hacer?", ["📝 Clasificar una queja manual", "📂 Clasificar archivo Excel/CSV"])

# === MODO 1: CLASIFICACIÓN MANUAL ===
if modo == "📝 Clasificar una queja manual":
    texto = st.text_area("✏️ Ingresá una queja", height=200)

    if st.button("📊 Clasificar queja"):
        if not texto.strip():
            st.warning("Ingresá una queja antes de clasificar.")
        else:
            with st.spinner("Clasificando..."):
                categoria, razon = clasificar_queja_con_razon(texto)
            if categoria == "ERROR":
                st.error(f"❌ Error: {razon}")
            else:
                st.success("✅ Clasificación exitosa")
                st.write(f"**📌 Categoría:** {categoria}")
                st.write(f"**💬 Razón:** {razon}")

# === MODO 2: CLASIFICACIÓN POR ARCHIVO ===
else:
    archivo = st.file_uploader("📁 Subí un archivo Excel (.xlsx) o CSV (.csv)", type=["xlsx", "csv"])

    if archivo:
        if archivo.name.endswith(".csv"):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)

        st.write("✅ Archivo cargado. Columnas:")
        st.write(df.columns.tolist())

        columna = st.selectbox("Seleccioná la columna con las quejas:", df.columns)
        espera = st.slider("⏱ Espera entre clasificaciones (segundos)", 0, 10, 5)

        if st.button("🚀 Clasificar archivo"):
            categorias = []
            razones = []
            total = len(df)
            progreso = st.progress(0)
            estado = st.empty()

            for i, texto in enumerate(df[columna].astype(str)):
                estado.text(f"Clasificando fila {i + 1} de {total}...")
                categoria, razon = clasificar_queja_con_razon(texto)
                categorias.append(categoria)
                razones.append(razon)
                progreso.progress((i + 1) / total)
                time.sleep(espera)

            df["Clasificacion-Gemini"] = categorias
            df["Razon-Gemini"] = razones

            # Descargar resultado
            salida = BytesIO()
            df.to_excel(salida, index=False)
            salida.seek(0)

            nombre_base = archivo.name.rsplit(".", 1)[0]
            nombre_resultado = f"{nombre_base}_clasificado.xlsx"

            st.success("✅ Clasificación completada")
            st.download_button(
                label="⬇️ Descargar archivo clasificado",
                data=salida,
                file_name=nombre_resultado,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )





##################################################

import pandas as pd
import time
import os
from tqdm import tqdm
from google.colab import drive

# Importa la librería 'google-genai'
import google.genai as genai
from google.genai import types
#from google.genai.types import GenerationConfig
# No necesitamos importar GenerationConfig si no vamos a usarlo
# from google.generativeai.types import GenerationConfig



# === CONFIGURACIÓN DE API KEY ===
MI_API_KEY = MI_API_KEY # <-- ¡Revisa que esta API Key sea válida y segura!

if not MI_API_KEY:
    raise ValueError("❌ No se encontró la API Key. Definila correctamente.")

# === PARÁMETROS DEL SCRIPT ===
archivo_entrada = "/content/drive/MyDrive/TPTM/quejas_1.xlsx"
archivo_salida = "/content/drive/MyDrive/TPTM/quejas_123579_clasificadas.xlsx" # Tu ruta corregida

columna_quejas = "Descripción del pasajero"
tiempo_espera = 10 # segundos de pausa entre clasificaciones

# === FUNCIÓN DE CLASIFICACIÓN ===
def clasificar_queja_con_razon(texto):
    prompt = f"""Leé la siguiente queja de un pasajero y devolvé SOLO:

1. La categoría más adecuada según esta lista:
- Servicio Operativo y Frecuencia
- Infraestructura y Mantenimiento
- Seguridad y Control
- Atención al Usuario
- Otros
- Conducta de Terceros
- Incidentes y Emergencias
- Accesibilidad y Público Vulnerable
- Personal y Desempeño Laboral
- Ambiente y Confort
- Tarifas y Boletos

2. Una breve razón de por qué fue clasificada así.

Formato de salida:
Categoría: <nombre de categoría>
Razón: <explicación>

Texto: {texto}
"""
    try:
        client = genai.Client(api_key=MI_API_KEY)

        # === ÚLTIMO INTENTO: ELIMINAR EL ARGUMENTO 'generation_config' ===
        # Si la función se queja de un argumento, la única solución es no pasarlo.
        # Esto significa que el modelo usará sus configuraciones por defecto.
        response = client.models.generate_content(
            model='gemini-2.0-flash-001', # Usando un modelo válido
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, top_p=1, top_k=1, max_output_tokens=256 ),
        )

        respuesta = response.text.strip()

        # Extraer categoría y razón
        categoria, razon = "", ""
        for linea in respuesta.splitlines():
            if linea.lower().startswith("categoría:") or linea.lower().startswith("categoria:"):
                categoria = linea.split(":", 1)[1].strip()
            elif linea.lower().startswith("razón:") or linea.lower().startswith("razon:"):
                razon = linea.split(":", 1)[1].strip()
        return categoria, razon

    except Exception as e:
        print(f"Error al clasificar texto: '{texto[:50]}...' - {e}")
        return "ERROR", str(e)

# === FUNCIÓN PARA PROCESAR EXCEL ===
def procesar_excel(archivo_entrada, columna_quejas, archivo_salida):
    try:
        df = pd.read_excel(archivo_entrada)
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        return

    if columna_quejas not in df.columns:
        print(f"❌ La columna '{columna_quejas}' no existe.")
        print("Columnas disponibles:", df.columns.tolist())
        return

    categorias = []
    razones = []

    print(f"🔍 Clasificando {len(df)} quejas...\n")

    for texto in tqdm(df[columna_quejas].astype(str), desc="Clasificando"):
        categoria, razon = clasificar_queja_con_razon(texto)
        categorias.append(categoria)
        razones.append(razon)
        if categoria != "ERROR":
            time.sleep(tiempo_espera)
        else:
            print("⚠️ Saltando la pausa debido a un error de clasificación.")

    df["Clasificacion-Gemini"] = categorias
    df["Razon-Gemini"] = razones

    try:
        df.to_excel(archivo_salida, index=False)
        print(f"\n✅ Archivo clasificado guardado en: {archivo_salida}")
    except Exception as e:
        print(f"❌ Error al guardar el archivo: {e}")

# === EJECUTAR ===
procesar_excel(archivo_entrada, columna_quejas, archivo_salida)
