import streamlit as st
import pandas as pd
import time
from io import BytesIO
import requests

# === CONFIGURACIÓN DE LA APP ===
st.set_page_config(page_title="Clasificador de Incidentes", layout="centered")
st.title("🧾 Clasificador de Incidentes Ferroviarios")

# === FUNCIÓN DE CLASIFICACIÓN LOCAL CON OLLAMA ===
def clasificar_incidente_ferroviario_con_razon(texto):
    prompt = f"""Leé la siguiente descripción de un incidente ferroviario y devolvé SOLO:

1. El Tipo de incidente más adecuado según la siguiente lista, basada en la definición, contexto y ejemplos proporcionados:
   - BARRERA ROTA:
     - Definición: Se entiende que hay un caso de barrera rota cuando se informa por el conductor o ayudente que cualquiera de sus brazos está roto.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'brazo ascendente o brazo descendente roto'. Además se suele mencionar el paso a nivel  con la barrera rota y la persona que informa (conductor o ayudante). Si no es informado por el conductor o ayudante no se considera un incidente. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares  y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel. Puede ser también que no se mencione si el brazo es ascendente o descendente.
     - Ejemplos: COND. CORREA M. (3116) INFORMA P.A.N. RIVADAVIA KM. 33/026, BRAZO DESCENDENTE ROTO. T. 3056/E706. SR. DEL VALLE SEÑALAMIENTO - SR. HERNANDEZ RESG. C/AVISO. SR. DEL VALLE DA EL NORMAL C/SEGURIDAD.-

   - BRAZOS DE BARRERA LEVANTADOS:
     - Definición: Se entiende que hay un caso de brazo de barrera levantado cuando cualquiera de sus brazos se informa por el conductor o ayudente que permanecen levantados.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'brazo ascendente permanece levantado o brazo descendente permanece levantado'. Además se suele mencionar el paso a nivel y la persona que informa. Si no es informado por el conductor o ayudante no se considera un incidente.
     - Ejemplos: COND. GUZMÁN J. (3068), DE T. 3074/E721, INFORMA QUE BRAZO DESCENDENTE DE P.A.N. RUTA 25 KM 51/434 PERMANECEN LEVANTADOS. MEC. BARRETO C/A. SR. BOGADO, RESG., C/A. MEC. DEL VALLE DA NORMAL, SIN CUSTODIA.

   - BRAZOS DE BARRERA GIRADOS HACIA LA VÍA:
     - Definición: Se entiende que hay un caso de brazo de barrera girado hacia la vía cuando cualquiera de sus brazos se encuentra girado hacia la zona de vía, puede ser en algunos casos que ocupen parte de la vía.
     - Ejemplos: COND. OLIVA (3125) TREN 3113 LOC. E705, COMUNICA P.A.N YRIGOYEN KM 15/649 BRAZO DESCENDENTE GIRADO HACIA ZONA DE VÍA. BARRIENTOS, SEÑALAMIENTO, C/A.PACHECO, RESG, C/A. MEC. BARRETO DA EL NORMAL, CON RESG.

   - INVASIÓN DE VÍA:
     - Definición: El conductor o ayudante aplica freno de emergencia por invasión de vía por persona, animal, vehículo u objeto.
     - Ejemplos: COND. CARBONEL (3023), T. 3154/E705 (4945-84), COMUNICA QUE APLICÓ  FRENO DE EMERGENCIA EN KM 38/400 PARA EVITAR ACCIDENTE DE PERSONA,LAS MISMAS SE CORRIERON Y COMENZARON A TIRAR PIEDRAS A LA FORMACIÓN. C/A. SR. MICALIZZI, RESG; SR. ACUÑA, VIDEO; AUX. MEDINA.

   - PARADA INCORRECTA:
     - Definición: La formación no queda alineada con el andén, puede deberse a falla o error de frenado.
     - Ejemplos: COND. MARTINEZ MILTON (3019) TREN 3039 LOC. E709 4984-45, COMUNICA EN ESTACIÓN VILLA ADELINA, PARADA INCORRECTA, QUEDANDO LOCOMOTORA Y MEDIO COCHE FUERA DE LA PLATAFORMA, MANIFIESTA QUE FUE UN ERROR DE CALCULO,  SIN CONSECUENCIA.

   - EXCESO DE VELOCIDAD:
     - Definición: La formación excede la velocidad máxima permitida para el tramo.
     - Ejemplos: CONTROLADOR GAVILAN DE CENTRO DE MONITOREO S.O.F.S.E. INFORMA POR  EXCESO DE VELOCIDAD DEL TREN 3086/E701 A 50 KM/H DEL KM. 39/000 AL  38/740. PRECAUCION DE 12 KM/H DEL KM. 39/070 AL 39/030 POR VÍA RENOVADA. C/A. SR. CODIGONI; SR. SERVIDIO; SR. GOMEZ DE VIDEO; AUX GONZALEZ. COND. VEGA D. (3050), COMUNICA QUE RESPETO LA PRECAUCION.

2. Una breve razón de por qué fue clasificado así, haciendo referencia a los detalles clave del texto que justifican la clasificación.

Formato de salida:
Tipo de Incidente: <nombre del tipo de incidente>
Razón: <explicación>

En caso de dudas sobre la clasificación, devolvé 'REVISAR' como Tipo de Incidente y una breve explicación.
Si no hay dudas y el texto no se corresponde con ninguno de los Tipos de Incidente proporcionados, devolvé 'FILA SIN EVENTOS' como Tipo de Incidente y una breve explicación.

Texto: {texto}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:14b",
                "prompt": prompt,
                "stream": False
            }
        )

        if response.status_code != 200:
            return "ERROR", f"Error {response.status_code}: {response.text}"

        output = response.json().get("response", "").strip()
        tipo_incidente, razon = "", ""

        for linea in output.splitlines():
            if linea.lower().startswith("tipo de incidente:"):
                tipo_incidente = linea.split(":", 1)[1].strip()
            elif linea.lower().startswith("razón:") or linea.lower().startswith("razon:"):
                razon = linea.split(":", 1)[1].strip()

        return tipo_incidente, razon

    except Exception as e:
        return "ERROR", str(e)


# === INTERFAZ STREAMLIT ===

modo = st.radio("¿Qué querés hacer?", ["📝 Clasificar un incidente manualmente", "📂 Clasificar archivo Excel/CSV"])

if modo == "📝 Clasificar un incidente manualmente":
    texto = st.text_area("✏️ Ingresá un texto", height=200)

    if st.button("📊 Clasificar"):
        if not texto.strip():
            st.warning("Ingresá un texto antes de clasificar.")
        else:
            with st.spinner("Clasificando..."):
                categoria, razon = clasificar_incidente_ferroviario_con_razon(texto)
            if categoria == "ERROR":
                st.error(f"❌ Error: {razon}")
            else:
                st.success("✅ Clasificación exitosa")
                st.write(f"**📌 Categoría:** {categoria}")
                st.write(f"**💬 Razón:** {razon}")

else:
    archivo = st.file_uploader("📁 Subí un archivo Excel (.xlsx) o CSV (.csv)", type=["xlsx", "csv"])

    if archivo:
        if archivo.name.endswith(".csv"):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)

        st.write("✅ Archivo cargado. Columnas:")
        st.write(df.columns.tolist())

        columna = st.selectbox("Seleccioná la columna con los posibles incidentes:", df.columns)
        espera = st.slider("⏱ Espera entre clasificaciones (segundos)", 0, 10, 2)

        if st.button("🚀 Clasificar archivo"):
            categorias = []
            razones = []
            total = len(df)
            progreso = st.progress(0)
            estado = st.empty()

            errores_consecutivos = 0
            limite_errores = 20

            for i, texto in enumerate(df[columna].astype(str)):
                estado.text(f"Clasificando fila {i + 1} de {total}...")

                try:
                    categoria, razon = clasificar_incidente_ferroviario_con_razon(texto)
                    if categoria == "ERROR":
                        errores_consecutivos += 1
                        razon = razon or "Error sin mensaje"
                    else:
                        errores_consecutivos = 0
                except Exception as e:
                    categoria = "ERROR"
                    razon = str(e)
                    errores_consecutivos += 1

                categorias.append(categoria)
                razones.append(razon)
                progreso.progress((i + 1) / total)

                if errores_consecutivos >= limite_errores:
                    st.error(f"❌ Se detectaron {errores_consecutivos} errores consecutivos. Se detiene la clasificación.")
                    break

                time.sleep(espera)

            df["Clasificacion-Deepseek"] = categorias
            df["Razon-Deepseek"] = razones

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
