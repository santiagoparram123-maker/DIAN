import pandas as pd
import os
import sys
import logging
from datetime import datetime
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from utils import normalize_nit
from dian_processor import check_nit_dian
from bdme_scraper import consult_batch_bdme

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_facturador_electronico(nit: str) -> bool:
    """
    [Simulado] Consulta la API de facturadores electrónicos de la DIAN.
    Retorna True si el NIT está habilitado para facturar, False en caso contrario o error.
    Para el MVP construiremos un mock basándonos en si el NIT termina en un digito par (simulando casos variados) 
    ya que no hay una API publica abierta sin autenticación institucional provista en el prompt.
    """
    nit_norm = normalize_nit(nit)
    try:
        # En producción aqui se haría un requests.get/post a la API oficial de facturación
        # simularemos una demora de red y un resultado heuristico determinístico
        logger.info(f"Consultando estado de facturador electrónico para NIT {nit_norm}")
        # Simulando resultado basado en NIT
        if int(nit_norm[-1]) % 2 == 0 or "900" in nit_norm:
            return True
        else:
             return False # simulamos no habilitados los impares para test de reglas
    except Exception as e:
        logger.error(f"Error consultando API facturador para {nit_norm}: {e}")
        return False

def calculate_risk(en_ficticios: bool, estado_bdme: str, facturador_habilitado: bool) -> tuple[str, str]:
    """
    Calcula el nivel de riesgo y la recomendación dada la matriz de reglas de precedencia:
    - NIT en Proveedores Ficticios (DIAN) -> ALTO
    - NIT en BDME como deudor moroso o no habilitado facturador -> MEDIO
    - Consulta BDME falló (INDETERMINADO) -> REVISAR
    - Ninguna alerta -> BAJO
    Retorna la tupla (Nivel, Recomendacion)
    """
    if en_ficticios:
        return "ALTO", "Bloquear pago + alerta inmediata"
    
    if estado_bdme == "EN_MORA" or not facturador_habilitado:
        return "MEDIO", "Revisar con asesor tributario antes de pagar"
        
    if estado_bdme == "INDETERMINADO":
        return "REVISAR", "Falla de consulta externa, verificar manualmente"
        
    return "BAJO", "Proveedor verificado — sin alertas"

def generate_report(client_excel_path: str, output_path: str = None) -> str:
    """
    Genera el reporte final evaluando el riesgo de cada NIT dado.
    """
    if not os.path.exists(client_excel_path):
        raise FileNotFoundError(f"Archivo de entrada del cliente no encontrado en {client_excel_path}")
        
    logger.info(f"Generando reporte a partir de: {client_excel_path}")
    
    # 1. Leer excel
    try:
        df_client = pd.read_excel(client_excel_path)
    except Exception as e:
        logger.error(f"Error parseando Excel cliente: {e}")
        raise ValueError("El archivo Excel del cliente está corrupto o tiene formato inválido.")
        
    # Validar columna NIT
    if 'NIT' not in [c.upper() for c in df_client.columns]:
         # Intentemos buscar cual es la de nit
         possible_nits = [c for c in df_client.columns if 'NIT' in str(c).upper() or 'IDENTIFICACION' in str(c).upper()]
         if not possible_nits:
             raise ValueError("No se encontró columna 'NIT' en el archivo.")
         else:
             nit_col = possible_nits[0]
    else:
         nit_col = df_client.columns[[c.upper() == 'NIT' for c in df_client.columns]][0]
         
    # 2. Normalizar NITs y remover nulos para la consulta
    def safe_normalize(x):
        try:
            return normalize_nit(x) if pd.notna(x) else None
        except ValueError:
            return None
            
    df_client['NIT_NORMALIZADO'] = df_client[nit_col].apply(safe_normalize)
    df_procesar = df_client.dropna(subset=['NIT_NORMALIZADO']).copy()
    
    nits_unicos = df_procesar['NIT_NORMALIZADO'].unique().tolist()
    
    # 3. Lote a BDME
    df_bdme = consult_batch_bdme(nits_unicos)
    
    # 4. Consolidar tabla de resultados
    resultados = []
    
    for _, row in df_procesar.iterrows():
        nit = row['NIT_NORMALIZADO']
        razon_social = row.get('RAZON_SOCIAL', row.get('NOMBRE', row.get('NOMBRE O RAZON SOCIAL', '')))
        
        # Validaciones
        en_ficticios = check_nit_dian(nit)
        
        # Buscar en cache lote
        if not df_bdme.empty and 'nit' in df_bdme.columns:
            bdme_info = df_bdme[df_bdme['nit'] == nit]
            estado_bdme = bdme_info['estado_bdme'].iloc[0] if not bdme_info.empty else "INDETERMINADO"
        else:
            estado_bdme = "INDETERMINADO"
        
        # API facturador
        fact_habilitado = check_facturador_electronico(nit)
        
        # Calcular riesgo
        riesgo, recomendacion = calculate_risk(en_ficticios, estado_bdme, fact_habilitado)
        
        resultados.append({
            "NIT": nit,
            "RAZON_SOCIAL": str(razon_social).strip(),
            "EN_FICTICIOS": en_ficticios,
            "ESTADO_BDME": estado_bdme,
            "FACTURADOR_HABILITADO": fact_habilitado,
            "NIVEL_RIESGO": riesgo,
            "RECOMENDACION": recomendacion
        })

    df_resultado = pd.DataFrame(resultados)
    
    # 5. Generar Excel
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_path:
        out_dir = os.path.join(os.path.dirname(__file__), '../outputs')
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"reporte_cumplimiento_{timestamp_str}.xlsx")
        
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Pestaña Detalle
            df_resultado.to_excel(writer, sheet_name='Detalle', index=False)
            
            # Pestaña Resumen
            total_analizados = len(df_resultado)
            if df_resultado.empty:
                # Columna mínima requerida para el resumen si está vacío
                counts = pd.Series(dtype=int)
            else:
                counts = df_resultado['NIVEL_RIESGO'].value_counts()
            
            resumen_data = {
                "Métrica": ["Total Analizados", "Total ALTO", "Total MEDIO", "Total REVISAR/INDETERMINADO", "Total BAJO", "Fecha Análisis"],
                "Valor": [
                    total_analizados,
                    counts.get("ALTO", 0),
                    counts.get("MEDIO", 0),
                    counts.get("REVISAR", 0),
                    counts.get("BAJO", 0),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Detalle']
            
            # Formatos condicionales de color
            from openpyxl.styles import PatternFill
            fill_rojo = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
            fill_naranja = PatternFill(start_color="FFE5CC", end_color="FFE5CC", fill_type="solid")
            fill_amarillo = PatternFill(start_color="FFFACC", end_color="FFFACC", fill_type="solid")
            fill_verde = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
            
            # Nivel es G (columna 6) - 1-indexed in openpyxl -> 'F' level col is 6
            for row in range(2, worksheet.max_row + 1):
                cell_riesgo = worksheet.cell(row=row, column=6).value
                fill_color = None
                if cell_riesgo == 'ALTO':
                    fill_color = fill_rojo
                elif cell_riesgo == 'MEDIO':
                    fill_color = fill_naranja
                elif cell_riesgo == 'REVISAR':
                    fill_color = fill_amarillo
                elif cell_riesgo == 'BAJO':
                    fill_color = fill_verde
                
                if fill_color:
                     for col in range(1, worksheet.max_column + 1):
                         worksheet.cell(row=row, column=col).fill = fill_color
                         
        logger.info(f"Reporte exitosamente guardado en: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error guardando Excel: {e}")
        raise

if __name__ == "__main__":
    # Test de Humo Report Engine
    # Crear un dummy excel client con NITs (Uno ficticio, otro no habilitado, otro de test)
    dummy_input = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/test_client_input.xlsx'))
    os.makedirs(os.path.dirname(dummy_input), exist_ok=True)
    pd.DataFrame({
        'NIT': ["900123456", "901565796", "801004345"], # El segundo esta en BDME, el tercero tambien
        'RAZON_SOCIAL': ["Empresa Dummy", "SERVICIOS & SUM", "COO SERVICIOS"]
    }).to_excel(dummy_input, index=False)
    
    print("Iniciando test de humo de report engine...")
    out_file = generate_report(dummy_input)
    print(f"✅ Test completado. Archivo en: {out_file}")
