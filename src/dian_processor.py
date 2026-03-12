import polars as pl
import os
from datetime import datetime
import logging
from utils import normalize_nit

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger("DianProcessor")

def process_dian_file(filepath: str) -> pl.DataFrame:
    """
    Lee el archivo Excel de la DIAN utilizando Polars para un procesamiento
    out-of-core más eficiente en memoria. Normaliza NITs, elimina duplicados,
    agrega FECHA_INGESTA y guarda el resultado en Parquet.
    """
    if not os.path.exists(filepath):
        logger.error(f"Archivo no encontrado: {filepath}")
        raise FileNotFoundError(f"El archivo esperado no se encontró en la ruta: {filepath}")

    logger.info(f"Cargando archivo (Out-of-Core con Polars): {filepath}")
    
    try:
        # Polars lee excel usando fastexcel o calamine bajo el capó (muy rápido)
        df_lazy = pl.read_excel(filepath).lazy()
    except Exception as e:
        logger.error(f"Error al leer el archivo Excel con Polars: {e}")
        raise

    # Validar que existe columna NIT
    found_columns = df_lazy.collect_schema().names()
    
    if 'NIT' not in found_columns:
        raise ValueError(f"Schema inválido. Columnas encontradas: {found_columns}. Se esperaba al menos la columna 'NIT'.")

    # Contar registros originales (requiere collect)
    # Si el archivo es gigantesco, podríamos omitir este count, pero para logs es útil
    df = df_lazy.collect()
    original_count = df.height
    
    # Normalizar NIT usando expresión map_elements para aplicar función Python
    logger.info("Normalizando NITs y eliminando duplicados...")
    # Convierte la columna a string primero (por si vienen ints) y aplica limpieza
    df = df.with_columns(
        pl.col('NIT').map_elements(normalize_nit, return_dtype=pl.Utf8).alias('NIT_NORMALIZADO')
    )
    
    # Eliminar duplicados basados en el NIT normalizado
    df = df.unique(subset=['NIT_NORMALIZADO'], keep='first', maintain_order=True)
    
    # Agregar FECHA_INGESTA
    df = df.with_columns(
        pl.lit(datetime.now()).alias('FECHA_INGESTA')
    )
    
    # Guardar en parquet
    output_dir = os.path.join(os.path.dirname(__file__), '../data')
    os.makedirs(output_dir, exist_ok=True)
    parquet_path = os.path.join(output_dir, 'dian_ficticios.parquet')
    
    df.write_parquet(parquet_path)
    
    # Log summary
    duplicates_removed = original_count - df.height
    logger.info(f"Procesamiento completado. Registros procesados: {df.height}. Duplicados eliminados: {duplicates_removed}.")
    logger.info(f"Archivo guardado en: {parquet_path}")
    
    return df

def check_nit_dian(nit: str) -> bool:
    """
    Verifica si un NIT normalizado está en la base de datos de ficticios de la DIAN,
    usando LazyFrames de Polars para búsquedas ultrarrápidas y bajo uso de memoria.
    """
    parquet_path = os.path.join(os.path.dirname(__file__), '../data/dian_ficticios.parquet')
    if not os.path.exists(parquet_path):
        logger.warning(f"La base de datos DIAN no existe en {parquet_path}. Debe ejecutarse process_dian_file primero.")
        return False
        
    try:
        # scan_parquet es out-of-core, no carga todo a RAM
        normalized_nit = normalize_nit(nit)
        lazy_df = pl.scan_parquet(parquet_path)
        
        # Filtramos y colectamos (solo trae los rows que coincidan, super eficiente)
        coincidencias = lazy_df.filter(pl.col("NIT_NORMALIZADO") == normalized_nit).collect()
        
        return coincidencias.height > 0
        
    except Exception as e:
        logger.error(f"Error al buscar en caché parquet: {e}")
        return False

if __name__ == "__main__":
    # Test de humo local
    test_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Proveedores-Ficticios-16022026.xlsx'))
    try:
        df_result = process_dian_file(test_file_path)
        print(f"✅ Procesados {df_result.height} registros")
        print(df_result.select(['NIT', 'NIT_NORMALIZADO', 'FECHA_INGESTA']).head())
    except Exception as e:
        print(f"❌ Error durante el test de humo: {e}")
