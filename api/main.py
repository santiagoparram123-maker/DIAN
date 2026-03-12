from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys
import os
import uvicorn
import logging

# Configurar ruta para importar módulos locales desde src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
try:
    from clasificador import clasificar_producto
except ImportError:
    logging.warning("No se pudo importar 'clasificador'. El endpoint de IA puede no funcionar si no existe src/clasificador.py")
    def clasificar_producto(desc):
        return {"hs_code": "0000000000", "confianza": "mocked"}

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

if __name__ == "__main__":
    # Inicia servidor Uvicorn para desarrollo
    print("\n🚀 Iniciando Microservicio DIAN Auditor en el puerto 8000...")
    print("👉 Swagger interactivo local en: http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
