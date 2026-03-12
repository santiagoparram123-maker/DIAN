import os
import logging
import polars as pl
from sodapy import Socrata
from typing import Optional

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger("SocrataClient")

class ColombiaOpenDataClient:
    """
    Cliente para consumir la API de Datos Abiertos de Colombia (Socrata) de forma automatizada.
    Implementa paginación explícita para manejar datasets masivos sin colapsar la memoria,
    utilizando Polars para la construcción eficiente del DataFrame final.
    """
    
    # Dominio de Datos Abiertos de Colombia
    DOMAIN = "www.datos.gov.co"
    
    def __init__(self, app_token: Optional[str] = None):
        """
        Inicializa el cliente de Socrata.
        
        Args:
            app_token (str, opcional): Token de aplicación de Socrata para evitar límites de tasa severos.
                                       Si es None, usará acceso público (límites más estrictos).
        """
        self.app_token = app_token or os.getenv("SOCRATA_APP_TOKEN")
        
        try:
            # Inicializamos el cliente. timeout en 60 segundos para evitar colgar en queries pesadas.
            self.client = Socrata(self.DOMAIN, self.app_token, timeout=60)
            logger.info("Cliente Socrata inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar cliente Socrata: {e}")
            raise

    def fetch_dataset_paginated(self, dataset_identifier: str, limit_per_page: int = 50000, 
                                max_records: Optional[int] = None, select_query: Optional[str] = None) -> pl.DataFrame:
        """
        Descarga un dataset completo (o hasta max_records) manejando la paginación automáticamente
        y construye un Polars DataFrame out-of-core compatible.
        
        Args:
            dataset_identifier (str): Identificador único del dataset (ej: 'xdk5-pm3f')
            limit_per_page (int): Cantidad de registros a traer por cada petición (chunk size).
            max_records (int, opcional): Límite total de registros a traer (útil para pruebas).
            select_query (str, opcional): Columnas específicas a traer (SoQL form).
        
        Returns:
            pl.DataFrame: DataFrame de Polars con los datos obtenidos.
        """
        logger.info(f"Iniciando descarga paginada del dataset: {dataset_identifier}")
        
        all_chunks = []
        offset = 0
        total_fetched = 0
        
        while True:
            # Calcular cuánto pedir en esta iteración
            current_limit = limit_per_page
            if max_records is not None:
                remaining = max_records - total_fetched
                if remaining <= 0:
                    break
                current_limit = min(limit_per_page, remaining)
            
            logger.info(f"Fetching chunk... offset: {offset}, limit: {current_limit}")
            
            try:
                # kwargs para la consulta SoQL
                query_kwargs = {"limit": current_limit, "offset": offset}
                if select_query:
                    query_kwargs["select"] = select_query
                    
                # Llamada a la API
                results = self.client.get(dataset_identifier, **query_kwargs)
                
                # Si no retorna resultados, significa que llegamos al final del dataset
                if not results:
                    break
                    
                # Convertir lista de dicts a Polars DataFrame
                chunk_df = pl.DataFrame(results)
                all_chunks.append(chunk_df)
                
                fetched_in_chunk = chunk_df.height
                total_fetched += fetched_in_chunk
                offset += current_limit
                
                # Si trajo menos registros que el límite, también significa el final
                if fetched_in_chunk < current_limit:
                    break
                    
            except Exception as e:
                logger.error(f"Error al descargar chunk en offset {offset}: {e}")
                # En producción podríamos implementar retries exponenciales aquí
                raise
                
        if not all_chunks:
            logger.warning("No se obtuvieron datos de la API.")
            return pl.DataFrame()
            
        # Concatenar todos los chunks en un solo DataFrame eficientemente
        logger.info(f"Concatenando {len(all_chunks)} chunks para formar el DataFrame final...")
        final_df = pl.concat(all_chunks, how="vertical_relaxed")
        
        logger.info(f"Descarga completada. Total registros: {final_df.height}")
        return final_df

if __name__ == "__main__":
    # Test de humo local
    # UUID de un dataset real y pequeño de ejemplo en datos.gov.co
    # Por ejemplo, el dataset de Proveedores Ficticios o similar si existe.
    # Aquí usaremos un UUID de ejemplo. Idealmente se pasa por entorno.
    
    # Dataset de prueba: "Gastos de Viaje" u otro público pequeño
    TEST_DATASET_ID = "32sa-8pi3" # UUID de ejemplo (indicadores, trm, etc)
    
    print("="*50)
    print("Test de Cliente Socrata Open Data")
    print("="*50)
    
    client = ColombiaOpenDataClient()
    
    try:
        # Traeremos solo 1000 registros para no demorar el script
        df_result = client.fetch_dataset_paginated(TEST_DATASET_ID, limit_per_page=500, max_records=1000)
        print(f"\n✅ Datos obtenidos exitosamente: {df_result.height} filas")
        if df_result.height > 0:
            print("\nMuestra de datos:")
            print(df_result.head())
    except Exception as e:
        print(f"\n❌ Prueba conectividad falló: {e}")
        print("Nota: Verifica tu conexión a internet o el Dataset ID.")
