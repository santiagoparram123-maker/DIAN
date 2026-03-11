import pandas as pd
import os
from datetime import datetime
import logging
from utils import normalize_nit

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_dian_file(filepath: str) -> pd.DataFrame:
    """
    Lee el archivo Excel de la DIAN, normaliza NITs, elimina duplicados,
    agrega FECHA_INGESTA y guarda el resultado en Parquet.
    """
    if not os.path.exists(filepath):
        logger.error(f"Archivo no encontrado: {filepath}")
        raise FileNotFoundError(f"El archivo esperado no se encontró en la ruta: {filepath}")

    logger.info(f"Cargando archivo: {filepath}")
    
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        logger.error(f"Error al leer el archivo Excel: {e}")
        raise

    # Validar que existe columna NIT
    expected_columns = ['NIT']
    found_columns = df.columns.tolist()
    
    # Check if 'NIT' is in columns (case-insensitive or exact match? Let's look for exact first, or check if any column contains 'NIT')
    if 'NIT' not in found_columns:
        # PDR says expected columns: "al menos una columna de NIT/identificación"
        # The sample has exact column "NIT"
        raise ValueError(f"Schema inválido. Columnas encontradas: {found_columns}. Se esperaba al menos la columna 'NIT'.")

    # Guardar cantidad original
    original_count = len(df)
    
    # Normalizar NIT
    df['NIT_NORMALIZADO'] = df['NIT'].apply(normalize_nit)
    
    # Eliminar duplicados basados en el NIT normalizado
    df = df.drop_duplicates(subset=['NIT_NORMALIZADO'], keep='first')
    
    # Agregar FECHA_INGESTA
    df['FECHA_INGESTA'] = datetime.now()
    
    # Guardar en parquet
    output_dir = os.path.join(os.path.dirname(__file__), '../data')
    os.makedirs(output_dir, exist_ok=True)
    parquet_path = os.path.join(output_dir, 'dian_ficticios.parquet')
    
    df.to_parquet(parquet_path, index=False)
    
    # Log summary
    duplicates_removed = original_count - len(df)
    logger.info(f"Procesamiento completado. Registros procesados: {len(df)}. Duplicados eliminados: {duplicates_removed}.")
    logger.info(f"Archivo guardado en: {parquet_path}")
    
    return df

def check_nit_dian(nit: str) -> bool:
    """
    Verifica si un NIT normalizado está en la base de datos de ficticios de la DIAN.
    """
    parquet_path = os.path.join(os.path.dirname(__file__), '../data/dian_ficticios.parquet')
    if not os.path.exists(parquet_path):
        logger.warning(f"La base de datos DIAN no existe en {parquet_path}. Debe ejecutarse process_dian_file primero.")
        return False
        
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        logger.error(f"Error al leer caché parquet: {e}")
        return False
        
    normalized_nit = normalize_nit(nit)
    return normalized_nit in df['NIT_NORMALIZADO'].values

if __name__ == "__main__":
    # Test de humo local
    test_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Proveedores-Ficticios-16022026.xlsx'))
    try:
        df_result = process_dian_file(test_file_path)
        print(f"✅ Procesados {len(df_result)} registros")
        print(df_result[['NIT', 'NIT_NORMALIZADO', 'FECHA_INGESTA']].head())
    except Exception as e:
        print(f"❌ Error durante el test de humo: {e}")
