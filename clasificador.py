import streamlit as st
import pandas as pd
import time
from io import BytesIO
import os
import google.generativeai as genai

# === CONFIGURACIÓN BÁSICA DE LA APP ===
#st.set_page_config(page_title="Clasificador de Quejas", layout="centered")


# Obtener el código válido desde variable de entorno (o valor por defecto para pruebas)
codigo_valido = os.getenv("CODIGO_ACCESO", "clasificar2024")

# Inicializar estado de sesión
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Si no está autenticado, mostrar formulario y detener app si no es válido
if not st.session_state.autenticado:
    with st.form("form_codigo"):
        st.markdown("### 🔒 Acceso restringido")
        codigo = st.text_input("Ingresá el código de acceso:", type="password")
        submit = st.form_submit_button("Ingresar")

    if submit:
        if codigo == codigo_valido:
            st.session_state.autenticado = True
            st.rerun()  # volver a cargar sin el formulario
        else:
            st.error("❌ Código incorrecto.")
    st.stop()  # Detener todo lo demás hasta que esté autenticado

# === CONFIGURACIÓN DE GEMINI ===
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key no configurada. Definila como variable de entorno GEMINI_API_KEY en Streamlit Cloud.")
    st.stop()

genai.configure(api_key=API_KEY)

# === FUNCIÓN DE CLASIFICACIÓN DE INCIDENTES FERROVIARIOS ===
def clasificar_incidente_ferroviario_con_razon(texto):
    prompt = f"""Leé la siguiente descripción de un incidente ferroviario y devolvé SOLO:

1. El Tipo de incidente más adecuado según la siguiente lista, basada en la definición, contexto y ejemplos proporcionados:
   - BARRERA ROTA:
     - Definición: Se entiende que hay un caso de barrera rota cuando se informa por el conductor o ayudente que cualquiera de sus brazos está roto.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'brazo ascendente o brazo descendente roto'. Además se suele mencionar el paso a nivel  con la barrera rota y la persona que informa (conductor o ayudante). Si no es informado por el conductor o ayudante no se considera un incidente. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares  y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel. Puede ser también que no se mencione si el barzo es ascendente o descendente.
     - Ejemplos: COND. CORREA M. (3116) INFORMA P.A.N. RIVADAVIA KM. 33/026, BRAZO DESCENDENTE ROTO. T. 3056/E706. SR. DEL VALLE SEÑALAMIENTO - SR. HERNANDEZ RESG. C/AVISO. SR. DEL VALLE DA EL NORMAL C/SEGURIDAD.-

   - BRAZOS DE BARRERA LEVANTADOS:
     - Definición: Se entiende que hay un caso de brazo de barrera girado hacia la vía  cuando cualquiera de sus brazos  se informa por el conductor o ayudente se encuentran girados hacia la zona de vía, puede ser en algunos casos que ocupen parte de la vía.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'brazo ascendente permanece levantado o brazo descendente permanece levantado'. Además se suele mencionar el paso a nivel  con el brazo levantado y la persona que informa (conductor o ayudante). Si no es informado por el conductor o ayudante no se considera un incidente. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares  y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel. Puede ser también que no se mencione si el barzo es ascendente o descendente.
     - Ejemplos: COND. GUZMÁN J. (3068), DE T. 3074/E721, INFORMA QUE BRAZO DESCENDENTE DE P.A.N. RUTA 25 KM 51/434 PERMANECEN LEVANTADOS. MEC. BARRETO C/A. SR. BOGADO, RESG., C/A. MEC. DEL VALLE DA NORMAL, SIN CUSTODIA.

   - BRAZOS DE BARRERA GIRADOS HACIA LA VÍA:
     - Definición: Se entiende que hay un caso de brazo de barrera girado hacia la vía cuando cualquiera de sus brazos  se encuentra girado hacia la zona de vía, puede ser en algunos casos que ocupen parte de la vía.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'brazo ascendente girado hacia la vía o brazo descendente girado hacia la vía'. Además se suele mencionar el paso a nivel  con el brazo girado y la persona que informa (conductor o ayudante). Si no es informado por el conductor o ayudante no se considera un incidente. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel. Puede ser también que no se mencione si el barzo es ascendente o descendente.
     - Ejemplos: COND. OLIVA (3125) TREN 3113 LOC. E705, COMUNICA P.A.N YRIGOYEN KM 15/649 BRAZO DESCENDENTE GIRADO HACIA ZONA DE VÍA. BARRIENTOS, SEÑALAMIENTO, C/A.PACHECO, RESG, C/A. MEC. BARRETO DA EL NORMAL, CON RESG.
      
   - INVASIÓN DE VÍA:
     - Definición: Se entiende que hay un caso de invasión de vía cuando el conductor o ayudante tiene que aplicar el freno de emergencia debido a la invasión u ocupación de la vía por una persona, animal,  vehículo u otro objeto que cruza, ocupa o transita sobre las vías de modo que puede ocasionar un accidente.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'conductor o ayudante aplicó freno de emergencia para evitar accidente de persona', 'conductor o ayudante aplicó freno de emergencia para evitar arrollar a animal (caballo, vaca, perro, etc.)' o 'conductor o ayudante aplicó freno de emergencia para evitar colisión o arrollar un vehículo'. Además se suele mencionar el paso a nivel o la progresiva de la vía (kilómetro) del incidente y la persona que informa el hecho. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel.
     - Ejemplos: COND. CARBONEL (3023), T. 3154/E705 (4945-84), COMUNICA QUE APLICÓ  FRENO DE EMERGENCIA EN KM 38/400 PARA EVITAR ACCIDENTE DE PERSONA,LAS MISMAS SE CORRIERON Y COMENZARON A TIRAR PIEDRAS A LA FORMACIÓN. C/A. SR. MICALIZZI, RESG; SR. ACUÑA, VIDEO; AUX. MEDINA. DETENIDO 04 MINUTOS EN EST. GRAND BOURG, GDA. GONZALEZ (72042) CHEQUEA FORMACIÓN PARA VER SI HAY PASAJEROS LESIONADOS; SIN CONSECUENCIA.

   - PARADA INCORRECTA:
     - Definición: Se entiende que hay un caso de parada incorrecta cuando la formación (tren) no queda alineada con respecto a la zona habilitada para el ascenso y descenso de pasajeros (andén), puede ser que la formación quede antes o después de la zona. Usualmente sucede por deficiencias en los frenos o error en la aplicación del freno.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'parada incorrecta'. Además se suele mencionar el nombre de la persona que informa el hecho, el nombre de la estación en que ocurre y la cantidad de coches que quedaron fuera de la plataforma o andén. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel.
     - Ejemplos: COND. MARTINEZ MILTON (3019) TREN 3039 LOC. E709 4984-45, COMUNICA EN ESTACIÓN VILLA ADELINA, PARADA INCORRECTA, QUEDANDO LOCOMOTORA Y MEDIO COCHE FUERA DE LA PLATAFORMA, MANIFIESTA QUE FUE UN ERROR DE CALCULO,  SIN CONSECUENCIA. ALBARRACIN, INFORMES, C/A. CASTILLO, C/A. VIDEO, C/A.

   - EXCESO DE VELOCIDAD:
     - Definición: Se entiende que hay un caso de exceso de velocidad cuando una formación (tren) supera el límite permitido para un determinado tramo de vía.
     - Contexto: Usualmente, pero no siempre, en el texto se encuentra este tipo de incidente como 'exceso de velocidad'. Además se suele mencionar el número de tren, la velocidad del tren, la progresiva o kilómetro del hecho, y la persona que informa el hecho. En el texto suele haber abreviaturas, por ejemplo 'COND.' para conductor, 'AYTE' para ayudante; aunque pueden aparecer de otras maneras similares y otras abreviaturas, son muy comunes ZDV para zona de vías y PAN o P.A.N. para paso a nivel.
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
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        respuesta = response.text.strip()

        tipo_incidente, razon = "", ""
        for linea in respuesta.splitlines():
            if linea.lower().startswith("tipo de incidente:"):
                tipo_incidente = linea.split(":", 1)[1].strip()
            elif linea.lower().startswith("razón:") or linea.lower().startswith("razon:"):
                razon = linea.split(":", 1)[1].strip()
        return tipo_incidente, razon

    except Exception as e:
        return "ERROR", str(e)


# === INTERFAZ STREAMLIT ===
st.set_page_config(page_title="Clasificador de Incidentes", layout="centered")
st.title("🧾 Clasificador de Incidentes")

modo = st.radio("¿Qué querés hacer?", ["📝 Clasificar un incidente manualmente", "📂 Clasificar archivo Excel/CSV"])

# === MODO 1: CLASIFICACIÓN MANUAL ===
if modo == "📝 Clasificar una incidente manualmente":
    texto = st.text_area("✏️ Ingresá una queja", height=200)

    if st.button("📊 Clasificar queja"):
        if not texto.strip():
            st.warning("Ingresá una queja antes de clasificar.")
        else:
            with st.spinner("Clasificando..."):
                categoria, razon = clasificar_incidente_ferroviario_con_razon(texto)
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

        columna = st.selectbox("Seleccioná la columna con los posibles incidentes:", df.columns)
        espera = st.slider("⏱ Espera entre clasificaciones (segundos)", 0, 10, 5)

        if st.button("🚀 Clasificar archivo"):
            categorias = []
            razones = []
            total = len(df)
            progreso = st.progress(0)
            estado = st.empty()

            for i, texto in enumerate(df[columna].astype(str)):
                estado.text(f"Clasificando fila {i + 1} de {total}...")
                categoria, razon = clasificar_incidente_ferroviario_con_razon(texto)
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

if st.session_state.autenticado:
    if st.button("🔒 Cerrar sesión"):
        st.session_state.autenticado = False
