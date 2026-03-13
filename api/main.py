from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys
import os
import uvicorn
import logging
import tempfile
import shutil

# Configurar ruta para importar módulos locales desde src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
try:
    from clasificador import clasificar_producto, clasificar_catalogo
except ImportError:
    logging.warning("No se pudo importar 'clasificador'. El endpoint de IA puede no funcionar si no existe src/clasificador.py")
    def clasificar_producto(desc):
        return {"hs_code": "0000000000", "confianza": "mocked"}
    def clasificar_catalogo(ruta):
        import pandas as pd
        return pd.DataFrame([{"ID_PRODUCTO": "1", "DESCRIPCION_MERCANCIA": "mock", "HS_CODE": "0", "CONFIANZA": "error"}])

try:
    from report_engine import generate_report
except ImportError:
    logging.warning("No se pudo importar 'report_engine'. El endpoint de auditoría de terceros puede fallar.")
    def generate_report(ruta, output_path=None):
        return "mocked_path.xlsx"

# --- Modelos Pydantic para Validación ---
class ClassificationRequest(BaseModel):
    descripcion: str = Field(
        ..., 
        description="Descripción detallada de la mercancía. Ej: 'Zapatos de cuero para hombre'",
        min_length=5,
        max_length=1500
    )

class ClassificationResponse(BaseModel):
    hs_code: str = Field(..., description="Código del sistema armonizado (10 dígitos comúnmente)")
    confidence_score: str = Field(..., description="Nivel de confianza de la predicción (alta, media, baja)")
    
# --- Inicialización de FastAPI ---
app = FastAPI(
    title="DIAN Auditor B2B — Core API",
    description="Motor backend independiente que expone modelos de IA y reglas de cumplimiento.",
    version="1.0.0"
)

# CORS para permitir peticiones desde el frontend web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiar por dominios B2B esperados
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/health", tags=["System"])
def health_check():
    """Verifica que el microservicio esté en línea."""
    return {"status": "ok", "service": "DIAN Auditor API v1.0"}

@app.post("/classify", response_model=ClassificationResponse, tags=["IA Services"])
def classify_product(request: ClassificationRequest = Body(...)):
    """
    Recibe la descripción de una mercancía y retorna la predicción
    de su Partida / Subpartida Arancelaria (HS Code) usando el modelo
    de IA configurado en el backend.
    """
    try:
        # Llamar a la función principal del clasificador modularizado
        resultado = clasificar_producto(request.descripcion)
        
        # Mapear diccionarios
        return ClassificationResponse(
            hs_code=resultado.get("hs_code", "ERROR"),
            confidence_score=resultado.get("confianza", "error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno clasificando: {str(e)}")

@app.post("/api/auditar-terceros", tags=["Comercial"])
async def auditar_terceros(file: UploadFile = File(...)):
    """
    Recibe un archivo Excel/CSV con NITs, orquesta la revisión DIAN/BDME
    y devuelve el archivo Excel resultante con las validaciones y colores.
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel o CSV")
    
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
            
        output_excel_path = generate_report(tmp_path)
        
        os.remove(tmp_path)
        
        # Verificar que generate_report devolvió un output
        if not output_excel_path or not os.path.exists(output_excel_path):
            raise HTTPException(status_code=500, detail="Fallo en la generación del reporte.")
            
        return FileResponse(
            path=output_excel_path, 
            filename=f"Auditado_{file.filename}.xlsx" if not file.filename.endswith('.xlsx') else f"Auditado_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logging.error(f"Error auditando terceros: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clasificar-masivo", tags=["Comercial"])
async def clasificar_masivo(file: UploadFile = File(...)):
    """
    Recibe un archivo CSV de mercancías, lo clasifica masivamente usando 
    el modelo de IA predictiva Ollama y devuelve un JSON estructurado con los resultados.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
            
        df_resultados = clasificar_catalogo(tmp_path)
        
        os.remove(tmp_path)
        
        # Convertir el DataFrame a una lista de diccionarios
        resultados_json = df_resultados.to_dict(orient='records')
        return resultados_json
    except Exception as e:
        logging.error(f"Error clasificando masivamente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Inicia servidor Uvicorn para desarrollo
    print("\n🚀 Iniciando Microservicio DIAN Auditor en el puerto 8000...")
    print("👉 Swagger interactivo local en: http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
