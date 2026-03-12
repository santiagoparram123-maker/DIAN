# ============================================================================
# MÓDULO: Auto-Clasificador Arancelario Masivo
# Archivo: src/clasificador.py
# Proyecto: DIAN Auditor B2B — Compliance Aduanero para Colombia
# Autor: Santiago — Portafolio de Ciencia de Datos
# ============================================================================
#
# DESCRIPCIÓN:
# Este módulo implementa un clasificador arancelario automatizado que utiliza
# el modelo de lenguaje qwen2.5-coder:7b (ejecutado localmente con Ollama)
# para asignar códigos HS (Harmonized System) de 10 dígitos a mercancías
# descritas en texto libre. Diseñado para agencias de aduanas que necesitan
# clasificar catálogos masivos de productos importados a Colombia.
#
# FLUJO DE DATOS:
# CSV (ID_PRODUCTO, DESCRIPCION_MERCANCIA)
#   → Pandas DataFrame
#     → Iteración por cada descripción
#       → Prompt a qwen2.5-coder:7b vía Ollama API local
#         → Parseo JSON con manejo de errores robusto
#           → DataFrame de resultados con HS Code + nivel de confianza
#             → JSON exportable para el frontend
#
# DEPENDENCIAS:
# - pandas: Manipulación de datos tabulares
# - requests: Comunicación HTTP con el servidor Ollama
# - json, re: Parseo y limpieza de respuestas del modelo
# ============================================================================

import pandas as pd
import requests
import json
import re
import os
import sys
import logging
from typing import Optional

# --- Configuración del Logger ---
# Formato profesional con timestamp para rastreo en producción
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)
logger = logging.getLogger("ClasificadorArancelario")

# ============================================================================
# CONSTANTES DE CONFIGURACIÓN
# ============================================================================

# Endpoint del servidor Ollama corriendo localmente.
# Por defecto Ollama escucha en el puerto 11434.
OLLAMA_URL = "http://localhost:11434/api/generate"

# Nombre exacto del modelo a invocar.
# IMPORTANTE: NO se usa OpenAI. Se usa qwen2.5-coder:7b via Ollama.
MODELO_IA = "qwen2.5-coder:7b"

# Columnas esperadas en el CSV de entrada del cliente
COLUMNA_ID = "ID_PRODUCTO"
COLUMNA_DESCRIPCION = "DESCRIPCION_MERCANCIA"

# ============================================================================
# SYSTEM PROMPT — Instrucciones estrictas para el modelo de IA
# ============================================================================
# Este prompt está diseñado para forzar al LLM a actuar exclusivamente como
# un clasificador arancelario experto. Se enfatiza que la ÚNICA salida válida
# es un objeto JSON, sin texto adicional, sin explicaciones, sin markdown.
# Esto minimiza errores de parseo y permite integración directa con el pipeline.

SYSTEM_PROMPT = """Eres un experto clasificador arancelario del Sistema Armonizado (SA/HS).
Tu ÚNICA función es analizar descripciones de mercancías y asignar el código arancelario correcto.

REGLAS ESTRICTAS:
1. Tu respuesta DEBE ser ÚNICAMENTE un objeto JSON válido. NADA MÁS.
2. NO incluyas explicaciones, comentarios, texto adicional ni formato markdown.
3. El código HS debe tener exactamente 10 dígitos (subpartida arancelaria completa).
4. Usa el arancel de aduanas de Colombia basado en la NANDINA y el Sistema Armonizado.
5. Si no estás seguro del código exacto, proporciona el más cercano y marca confianza como "baja".

FORMATO DE RESPUESTA (JSON puro, sin ```json ni texto):
{"hs_code": "6403990000", "confianza": "alta"}

NIVELES DE CONFIANZA:
- "alta": Clasificación clara y precisa basada en la descripción.
- "media": Descripción ambigua, múltiples partidas posibles. Se eligió la más probable.
- "baja": Descripción insuficiente o producto muy genérico. Requiere revisión humana."""


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def cargar_csv(ruta_csv: str) -> pd.DataFrame:
    """
    Lee y valida un archivo CSV con descripciones de productos.

    El CSV debe contener al menos dos columnas:
    - ID_PRODUCTO: Identificador único del producto (str o int)
    - DESCRIPCION_MERCANCIA: Texto libre describiendo la mercancía

    Args:
        ruta_csv (str): Ruta absoluta o relativa al archivo CSV.

    Returns:
        pd.DataFrame: DataFrame con las columnas validadas.

    Raises:
        FileNotFoundError: Si el archivo no existe en la ruta especificada.
        ValueError: Si el CSV no contiene las columnas requeridas.
    """
    # Verificar existencia del archivo
    if not os.path.exists(ruta_csv):
        logger.error(f"Archivo no encontrado: {ruta_csv}")
        raise FileNotFoundError(f"El archivo CSV no se encontró en: {ruta_csv}")

    logger.info(f"Cargando archivo CSV: {ruta_csv}")

    # Leer el CSV con pandas, intentando detectar el separador automáticamente
    try:
        df = pd.read_csv(ruta_csv, encoding='utf-8')
    except UnicodeDecodeError:
        # Algunos CSVs de Windows usan codificación latin-1
        logger.warning("Error de encoding UTF-8, reintentando con latin-1...")
        df = pd.read_csv(ruta_csv, encoding='latin-1')

    # Validar que las columnas requeridas estén presentes
    columnas_requeridas = {COLUMNA_ID, COLUMNA_DESCRIPCION}
    columnas_encontradas = set(df.columns.tolist())

    if not columnas_requeridas.issubset(columnas_encontradas):
        columnas_faltantes = columnas_requeridas - columnas_encontradas
        raise ValueError(
            f"El CSV no contiene las columnas requeridas. "
            f"Faltantes: {columnas_faltantes}. "
            f"Columnas encontradas: {list(columnas_encontradas)}. "
            f"Se esperaban: {list(columnas_requeridas)}"
        )

    # Eliminar filas donde la descripción esté vacía o sea NaN
    filas_originales = len(df)
    df = df.dropna(subset=[COLUMNA_DESCRIPCION])
    df[COLUMNA_DESCRIPCION] = df[COLUMNA_DESCRIPCION].astype(str).str.strip()
    df = df[df[COLUMNA_DESCRIPCION] != '']

    filas_eliminadas = filas_originales - len(df)
    if filas_eliminadas > 0:
        logger.warning(
            f"Se eliminaron {filas_eliminadas} filas con descripciones vacías o nulas."
        )

    logger.info(f"CSV cargado exitosamente. {len(df)} productos para clasificar.")
    return df


def clasificar_producto(descripcion: str) -> dict:
    """
    Envía la descripción de un producto al modelo qwen2.5-coder:7b via Ollama
    y retorna el HS Code con su nivel de confianza.

    El modelo recibe un system prompt estricto que lo obliga a responder
    exclusivamente en formato JSON. Si el modelo devuelve texto libre o
    JSON malformado, se implementa un proceso de limpieza con regex
    y un fallback a valores de error.

    Args:
        descripcion (str): Texto libre describiendo la mercancía a clasificar.
                          Ej: "Zapatos de cuero italiano con suela de caucho para hombre"

    Returns:
        dict: Diccionario con las claves:
              - "hs_code" (str): Código arancelario de 10 dígitos o "ERROR"
              - "confianza" (str): "alta", "media", "baja" o "error"
    """
    # Valor por defecto en caso de error total
    resultado_error = {"hs_code": "ERROR", "confianza": "error"}

    # Construir el prompt del usuario para esta mercancía específica
    prompt_usuario = (
        f"Clasifica la siguiente mercancía y responde SOLO con el JSON:\n"
        f"Mercancía: \"{descripcion}\""
    )

    # Payload para la API de generación de Ollama
    # Documentación: https://github.com/ollama/ollama/blob/main/docs/api.md
    payload = {
        "model": MODELO_IA,
        "prompt": prompt_usuario,
        "system": SYSTEM_PROMPT,
        "stream": False,          # Respuesta completa (no streaming)
        "options": {
            "temperature": 0.1,   # Baja temperatura para respuestas determinísticas
            "num_predict": 100    # Limitar tokens de salida (el JSON es corto)
        }
    }

    try:
        # --- LLAMADA AL MODELO ---
        # Se comunica con el servidor Ollama local via HTTP POST
        logger.info(f"Clasificando: \"{descripcion[:60]}...\"")
        respuesta = requests.post(OLLAMA_URL, json=payload, timeout=120)
        respuesta.raise_for_status()  # Lanza excepción si HTTP != 200

        # Extraer el texto generado por el modelo
        datos_respuesta = respuesta.json()
        texto_generado = datos_respuesta.get("response", "").strip()

        logger.debug(f"Respuesta cruda del modelo: {texto_generado}")

        # --- PARSEO DEL JSON ---
        # Intento 1: Parsear directamente como JSON válido
        try:
            resultado = json.loads(texto_generado)
            # Validar que las claves esperadas estén presentes
            if "hs_code" in resultado and "confianza" in resultado:
                # Sanitizar: asegurar que hs_code sean solo dígitos
                resultado["hs_code"] = re.sub(r'[^\d]', '', str(resultado["hs_code"]))
                # Validar nivel de confianza
                if resultado["confianza"] not in ("alta", "media", "baja"):
                    resultado["confianza"] = "media"
                return resultado
        except json.JSONDecodeError:
            pass  # Si falla, intentar limpieza con regex

        # Intento 2: El modelo a veces envuelve el JSON en markdown (```json ... ```)
        # o agrega texto antes/después. Intentamos extraer el JSON con regex.
        logger.warning("Respuesta no es JSON puro. Intentando extracción con regex...")
        patron_json = r'\{[^{}]*"hs_code"[^{}]*"confianza"[^{}]*\}'
        coincidencia = re.search(patron_json, texto_generado)

        if coincidencia:
            try:
                resultado = json.loads(coincidencia.group())
                resultado["hs_code"] = re.sub(r'[^\d]', '', str(resultado["hs_code"]))
                if resultado["confianza"] not in ("alta", "media", "baja"):
                    resultado["confianza"] = "media"
                return resultado
            except json.JSONDecodeError:
                pass

        # Intento 3: Buscar al menos un código numérico de 4+ dígitos
        logger.warning("No se encontró JSON válido. Buscando código numérico...")
        patron_codigo = r'\b(\d{4,10})\b'
        codigo_encontrado = re.search(patron_codigo, texto_generado)

        if codigo_encontrado:
            codigo = codigo_encontrado.group().ljust(10, '0')  # Rellenar a 10 dígitos
            return {"hs_code": codigo, "confianza": "baja"}

        # Si nada funcionó, retornar error
        logger.error(f"No se pudo parsear la respuesta del modelo: {texto_generado}")
        return resultado_error

    except requests.exceptions.ConnectionError:
        # El servidor Ollama no está corriendo
        logger.error(
            "No se pudo conectar al servidor Ollama. "
            "Asegúrate de que 'ollama serve' esté ejecutándose en localhost:11434"
        )
        return resultado_error

    except requests.exceptions.Timeout:
        # El modelo tardó demasiado en responder
        logger.error(f"Timeout al clasificar: \"{descripcion[:40]}...\"")
        return resultado_error

    except requests.exceptions.RequestException as e:
        # Cualquier otro error HTTP
        logger.error(f"Error HTTP al comunicarse con Ollama: {e}")
        return resultado_error

    except Exception as e:
        # Error inesperado (defensiva general)
        logger.error(f"Error inesperado durante clasificación: {e}")
        return resultado_error


def clasificar_catalogo(ruta_csv: str) -> pd.DataFrame:
    """
    Pipeline completo: carga un CSV de productos, clasifica cada uno con IA,
    y retorna un DataFrame enriquecido con los resultados.

    Esta es la función principal que orquesta todo el proceso de clasificación
    masiva. Puede procesar catálogos de cualquier tamaño, aunque el tiempo de
    ejecución dependerá del rendimiento del modelo local.

    Args:
        ruta_csv (str): Ruta al archivo CSV con las columnas
                       ID_PRODUCTO y DESCRIPCION_MERCANCIA.

    Returns:
        pd.DataFrame: DataFrame original enriquecido con las columnas:
                     - HS_CODE: Código arancelario asignado por la IA
                     - CONFIANZA: Nivel de confianza ("alta", "media", "baja", "error")
    """
    # Paso 1: Cargar y validar el CSV
    df = cargar_csv(ruta_csv)

    # Paso 2: Preparar listas para almacenar los resultados de la IA
    lista_hs_codes = []
    lista_confianzas = []
    total_productos = len(df)

    logger.info(f"Iniciando clasificación masiva de {total_productos} productos...")
    logger.info(f"Modelo: {MODELO_IA} | Endpoint: {OLLAMA_URL}")

    # Paso 3: Iterar sobre cada producto y clasificarlo individualmente
    # NOTA: Se procesa secuencialmente para no sobrecargar el modelo local.
    # En producción, se podría implementar concurrencia con asyncio o threading.
    for indice, fila in df.iterrows():
        descripcion = fila[COLUMNA_DESCRIPCION]
        numero_actual = len(lista_hs_codes) + 1

        logger.info(f"[{numero_actual}/{total_productos}] Procesando...")

        # Llamar al modelo para esta descripción
        resultado = clasificar_producto(descripcion)

        # Acumular los resultados
        lista_hs_codes.append(resultado["hs_code"])
        lista_confianzas.append(resultado["confianza"])

    # Paso 4: Agregar las columnas de resultado al DataFrame original
    df["HS_CODE"] = lista_hs_codes
    df["CONFIANZA"] = lista_confianzas

    # Paso 5: Resumen estadístico para el log
    conteo_confianza = df["CONFIANZA"].value_counts()
    logger.info("=" * 50)
    logger.info("CLASIFICACIÓN COMPLETADA — Resumen:")
    logger.info(f"  Total productos: {total_productos}")
    for nivel, conteo in conteo_confianza.items():
        porcentaje = (conteo / total_productos) * 100
        logger.info(f"  Confianza {nivel}: {conteo} ({porcentaje:.1f}%)")
    logger.info("=" * 50)

    return df


def exportar_json(df: pd.DataFrame, ruta_salida: Optional[str] = None) -> str:
    """
    Convierte el DataFrame de resultados a formato JSON orientado a registros,
    listo para ser consumido por el frontend JavaScript.

    Args:
        df (pd.DataFrame): DataFrame con las columnas de clasificación.
        ruta_salida (str, optional): Ruta para guardar el JSON en disco.
                                    Si es None, solo retorna el string.

    Returns:
        str: String JSON con los resultados de clasificación.

    Ejemplo de salida:
    [
        {
            "ID_PRODUCTO": "P001",
            "DESCRIPCION_MERCANCIA": "Zapatos de cuero italiano...",
            "HS_CODE": "6403990000",
            "CONFIANZA": "alta"
        },
        ...
    ]
    """
    # Convertir a JSON orientado a registros (lista de diccionarios)
    json_resultado = df.to_json(orient='records', force_ascii=False, indent=2)

    # Si se especificó ruta de salida, guardar en disco
    if ruta_salida:
        directorio = os.path.dirname(ruta_salida)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        with open(ruta_salida, 'w', encoding='utf-8') as archivo:
            archivo.write(json_resultado)
        logger.info(f"Resultados exportados a: {ruta_salida}")

    return json_resultado


# ============================================================================
# PUNTO DE ENTRADA — Ejecución como script independiente (CLI)
# ============================================================================
# Uso: python clasificador.py <ruta_al_csv>
# Ejemplo: python clasificador.py ../data/catalogo_ejemplo.csv

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 50)
        print("Auto-Clasificador Arancelario Masivo")
        print("=" * 50)
        print(f"\nUso: python {sys.argv[0]} <archivo.csv>")
        print(f"\nEl CSV debe contener las columnas:")
        print(f"  - {COLUMNA_ID}: Identificador del producto")
        print(f"  - {COLUMNA_DESCRIPCION}: Descripción de la mercancía")
        print(f"\nEjemplo: python {sys.argv[0]} ../data/catalogo_ejemplo.csv")
        sys.exit(1)

    ruta_archivo = sys.argv[1]

    try:
        # Ejecutar el pipeline completo de clasificación
        df_resultados = clasificar_catalogo(ruta_archivo)

        # Exportar resultados a JSON
        ruta_json = os.path.join(
            os.path.dirname(__file__), '..', 'outputs', 'clasificacion_resultado.json'
        )
        json_salida = exportar_json(df_resultados, ruta_json)

        # Mostrar vista previa de los resultados en consola
        print("\n" + "=" * 70)
        print("RESULTADOS DE CLASIFICACIÓN")
        print("=" * 70)
        columnas_mostrar = [COLUMNA_ID, COLUMNA_DESCRIPCION, "HS_CODE", "CONFIANZA"]
        print(df_resultados[columnas_mostrar].to_string(index=False))
        print("=" * 70)
        print(f"\n✅ Resultados exportados a: {ruta_json}")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error de validación: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
