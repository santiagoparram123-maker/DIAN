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
    from report_engine import generate_report, get_audit_data
except ImportError:
    logging.warning("No se pudo importar 'report_engine'. El endpoint de auditoría de terceros puede fallar.")
    def generate_report(ruta, output_path=None):
        return "mocked_path.xlsx"
    def get_audit_data(ruta):
        return [{"nit": "0", "razon_social": "error", "nivel_riesgo": "BAJO"}]

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

import pandas as pd
import io
import shutil
import tempfile

@app.post("/api/auditar-terceros", tags=["Comercial"])
async def auditar_terceros(file: UploadFile = File(...)):
    """
    Recibe un archivo Excel/CSV con NITs, orquesta la revisión DIAN/BDME
    y devuelve el archivo Excel resultante con las validaciones y colores.
    """
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel o CSV")
    
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
            
        output_excel_path = generate_report(tmp_path)
        
        if not output_excel_path or not os.path.exists(output_excel_path):
            raise HTTPException(status_code=500, detail="Fallo en la generación del reporte.")
            
        safe_filename = file.filename.lower().replace('.csv', '.xlsx').replace('.xls', '.xlsx')
        if not safe_filename.endswith('.xlsx'):
            safe_filename += '.xlsx'
            
        return FileResponse(
            path=output_excel_path, 
            filename=f"Auditado_{safe_filename}",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logging.error(f"Error auditando terceros: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/auditar-json", tags=["Comercial"])
async def auditar_json(file: UploadFile = File(...)):
    """
    Recibe un archivo Excel/CSV y devuelve los resultados en JSON
    directamente para mostrarlos en el Dashboard.
    """
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel o CSV")
        
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
            
        resultados = get_audit_data(tmp_path)
        return resultados
    except Exception as e:
        logging.error(f"Error procesando auditoría JSON: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/clasificar-masivo", tags=["Comercial"])
async def clasificar_masivo(file: UploadFile = File(...)):
    """
    Recibe un archivo CSV o Excel de mercancías, lo clasifica masivamente usando 
    el modelo de IA predictiva Ollama y devuelve un JSON estructurado con los resultados.
    """
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV o Excel")
        
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
            
        df_resultados = clasificar_catalogo(tmp_path)
        
        # Convertir el DataFrame a una lista de diccionarios
        resultados_json = df_resultados.to_dict(orient='records')
        return resultados_json
    except Exception as e:
        logging.error(f"Error clasificando masivamente: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Modelos para Reporte PDF ---
from pydantic import BaseModel as PydanticBaseModel
from typing import List, Optional as Opt

class PDFReportItem(PydanticBaseModel):
    id: str = ""
    descripcion: str = ""
    hs_code: str = ""
    confianza: str = ""
    nit: str = ""
    razon_social: str = ""
    nivel_riesgo: str = ""
    recomendacion: str = ""
    razonamiento: str = ""

class PDFReportRequest(PydanticBaseModel):
    titulo: str = "Reporte de Auditoría — DIAN Auditor B2B"
    tipo: str = "clasificacion"  # "clasificacion" o "auditoria"
    items: List[PDFReportItem]

@app.post("/api/generar-reporte-pdf", tags=["Reportes"])
async def generar_reporte_pdf(request: PDFReportRequest):
    """
    Genera un PDF profesional con los resultados de clasificación o auditoría.
    Incluye razonamiento del modelo IA para cada entrada.
    """
    try:
        from fpdf import FPDF
        
        class ReportePDF(FPDF):
            def header(self):
                self.set_fill_color(15, 23, 42)
                self.rect(0, 0, 210, 30, 'F')
                self.set_text_color(248, 250, 252)
                self.set_font('Helvetica', 'B', 16)
                self.cell(0, 15, request.titulo, ln=True, align='C')
                self.set_font('Helvetica', '', 9)
                self.cell(0, 8, f'Generado: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")} | DIAN Auditor B2B', ln=True, align='C')
                self.ln(5)
            
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(148, 163, 184)
                self.cell(0, 10, f'Pág. {self.page_no()}/{{nb}} — Documento generado automáticamente', align='C')

        pdf = ReportePDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=20)

        if request.tipo == "clasificacion":
            for i, item in enumerate(request.items):
                # Usar formato de tarjetas en lugar de tabla para acomodar textos largos
                pdf.set_fill_color(241, 245, 249)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(15, 23, 42)
                
                # Header Tarjeta
                conf_str = item.confianza.upper()
                pdf.cell(0, 8, f"ID: {item.id} | HS Code: {item.hs_code} | Confianza: {conf_str}", border=1, ln=True, fill=True)
                
                # Detalles Mercancía
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(0, 6, "Descripción de la Mercancía:", border='LR', ln=True)
                pdf.set_font('Helvetica', '', 9)
                # Reemplazo seguro de acentos con ignorar para compatibilidad Helvetica nativa fpdf2 en algunos sistemas
                safe_desc = str(item.descripcion).encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 5, safe_desc, border='LR')
                
                # Bloque de Razonamiento
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(0, 6, "Razonamiento del Modelo de IA:", border='LR', ln=True)
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(71, 85, 105) # slate-600
                safe_razon = str(item.razonamiento or "Sin razonamiento proveído.").encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 5, safe_razon, border='LRB')
                pdf.ln(4)

        else:  # auditoria
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(30, 41, 59)
            pdf.set_text_color(248, 250, 252)
            pdf.cell(30, 8, 'NIT', 1, 0, 'C', True)
            pdf.cell(55, 8, 'Razon Social', 1, 0, 'C', True)
            pdf.cell(25, 8, 'Riesgo', 1, 0, 'C', True)
            pdf.cell(80, 8, 'Recomendacion', 1, 1, 'C', True)

            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(30, 30, 30)
            
            for i, item in enumerate(request.items):
                if i % 2 == 0:
                    pdf.set_fill_color(241, 245, 249)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                safe_nit = str(item.nit)[:15]
                safe_rs = str(item.razon_social)[:35].encode('latin-1', 'replace').decode('latin-1')
                
                # Check height dynamically if needed, but for now stick to simple cells
                pdf.cell(30, 8, safe_nit, 1, 0, 'C', True)
                pdf.cell(55, 8, safe_rs, 1, 0, 'L', True)
                
                if item.nivel_riesgo == 'ALTO':
                    pdf.set_text_color(153, 27, 27)
                elif item.nivel_riesgo == 'MEDIO':
                    pdf.set_text_color(146, 64, 14)
                else:
                    pdf.set_text_color(21, 128, 61)
                pdf.cell(25, 8, item.nivel_riesgo, 1, 0, 'C', True)
                pdf.set_text_color(30, 30, 30)
                
                safe_rec = str(item.recomendacion or "N/A")[:50].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(80, 8, safe_rec, 1, 1, 'L', True)

        # Resumen final
        pdf.ln(10)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 8, f'Total de registros procesados: {len(request.items)}', ln=True)

        # Guardar PDF
        out_dir = os.path.join(os.path.dirname(__file__), '..', 'outputs')
        os.makedirs(out_dir, exist_ok=True)
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(out_dir, f"reporte_{request.tipo}_{timestamp}.pdf")
        pdf.output(pdf_path)

        return FileResponse(
            path=pdf_path,
            filename=f"Reporte_{request.tipo}_{timestamp}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        logging.error(f"Error generando PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Inicia servidor Uvicorn para desarrollo
    print("\n🚀 Iniciando Microservicio DIAN Auditor en el puerto 8000...")
    print("👉 Swagger interactivo local en: http://localhost:8000/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
