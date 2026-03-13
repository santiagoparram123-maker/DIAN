import sys
import os
import traceback
sys.path.append('src')
from report_engine import generate_report

try:
    print("Iniciando auditoría de prueba...")
    report_path = generate_report('prueba_03_estres_visual.csv.xlsx')
    print(f"Reporte generado en: {report_path}")
except Exception:
    traceback.print_exc()
