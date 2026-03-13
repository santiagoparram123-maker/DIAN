<h1 align="center">📊 Auditor de Riesgo Aduanero B2B — AAA Agency of AI 🧠</h1>

<p align="center">
  <b>Motor de Due Diligence Fiscal · Prevención de Proveedores Ficticios · Clasificación Arancelaria IA</b><br>
  <i>Micro-SaaS B2B — Cumplimiento DIAN · BDME · Facturadores Electrónicos</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/STATUS-PRODUCCIÓN_MVP-00C851?style=for-the-badge&logo=github">
  <img src="https://img.shields.io/badge/PYTHON-3.10+-F2C63C?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/API-FASTAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/IA-OLLAMA_QWEN2.5-8A2BE2?style=for-the-badge&logo=meta&logoColor=white">
  <img src="https://img.shields.io/badge/RAG-FAISS_+_MiniLM-FF6B35?style=for-the-badge">
  <img src="https://img.shields.io/badge/HARDWARE-CUDA_RTX_3050-76B900?style=for-the-badge&logo=nvidia&logoColor=white">
</p>

---

## 🧭 Descripción General

El **Auditor de Riesgo Aduanero B2B** es una herramienta core de la agencia **AAA Agency of AI**, diseñada para automatizar la auditoría de riesgos tributarios y la clasificación arancelaria de proveedores e importaciones en Colombia.

Opera como un **microservicio FastAPI** que combina tres motores principales:

1. **Motor de Due Diligence Fiscal** — Cruza NITs contra el Listado de Proveedores Ficticios (DIAN), el BDME (CHIP) y la base de Facturadores Electrónicos, generando matrices de riesgo (`ALTO` / `MEDIO` / `REVISAR` / `BAJO`) según el PDR del sistema.
2. **Clasificador Arancelario IA** — Asigna automáticamente Partidas HS Code a catálogos de importación usando `qwen2.5-coder:7b` vía Ollama con un pipeline RAG (Retrieval-Augmented Generation) acelerado por CUDA.
3. **Generador de Reportes** — Produce reportes Excel con formatos condicionales de color y PDFs con razonamiento del modelo IA.

> 💡 **Propuesta de valor:** No es "automatización" — es **prevención de multas y protección del patrimonio empresarial**. El cliente ideal (agencias de carga, e-commerce, empresas con muchos proveedores) ya siente el dolor y ya tiene el presupuesto para resolverlo.

---

## 📂 Estructura del Proyecto

```text
DIAN_Auditor_B2B
┣ 📂 api
┃ ┗ 📜 main.py              # Microservicio FastAPI (auditar-json, clasificar-masivo, generar-reporte-pdf)
┣ 📂 data
┃ ┣ 📂 raw                  # Proveedores-Ficticios-DIAN.xlsx (fuente oficial)
┃ ┣ 📂 samples              # Archivos de prueba (prueba_01/02/03)
┃ ┣ 📜 historico_dian.csv   # Knowledge base para el RAG
┃ ┣ 📜 dian_ficticios.parquet
┃ ┗ 📜 bdme_cache.parquet
┣ 📂 docs
┃ ┗ 📜 PDR_Auditor_DIAN.docx  # Project Definition Record (Arquitectura + Guardrails)
┣ 📂 outputs               # Reportes generados (Excel + PDF)
┣ 📂 src                   # Núcleo de negocio (Core — NO modificar sin PDR)
┃ ┣ 📜 clasificador.py     # RAG + Ollama qwen2.5-coder:7b + CUDA + LRU Cache
┃ ┣ 📜 report_engine.py    # Motor de auditoría de NITs con matriz de riesgo PDR
┃ ┣ 📜 dian_processor.py   # Procesador Polars de la base DIAN
┃ ┣ 📜 bdme_scraper.py     # Scraper BDME (CHIP)
┃ ┗ 📜 utils.py            # normalize_nit() — 9 dígitos, llave primaria PDR
┣ 📜 dashboard.html        # Portal de Auditoría de Terceros (Dark Theme B2B)
┣ 📜 clasificador.html     # Portal de Clasificación IA Masiva
┣ 📜 requirements.txt
┗ 📜 README.md
```

---

## 💻 Stack Tecnológico

| Tecnología | Descripción |
| :--- | :--- |
| **Python 3.10+** | Backend, procesamiento de datos y ML |
| **FastAPI + Uvicorn** | API asíncrona con documentación Swagger automática |
| **Ollama / qwen2.5-coder:7b** | Modelo de IA local para clasificación arancelaria |
| **FAISS + SentenceTransformers** | Pipeline RAG — top_k=10, similaridad coseno |
| **Polars + Pandas** | Procesamiento out-of-core de bases de datos masivas |
| **CUDA (RTX 3050)** | Aceleración GPU para embeddings y modelo IA |
| **fpdf2** | Generación de reportes PDF profesionales con razonamiento IA |
| **openpyxl + xlrd** | Compatibilidad universal Excel (XLS, XLSX, CSV-in-Excel) |
| **Selenium** | Consultas resilientes al BDME/CHIP |

---

## 🧠 Pipeline RAG — Clasificador Arancelario

```
Catálogo CSV/XLSX → cargar_archivo()
         ↓ (detección magic bytes + CSV-in-Excel)
    pd.DataFrame (ID, DESCRIPCIÓN)
         ↓
  SentenceTransformer.encode() [CUDA]
  + LRU Cache (maxsize=1000)
         ↓
  FAISS.search(top_k=10) → Ejemplos DIAN similares
         ↓
  Ollama qwen2.5-coder:7b
  [System Prompt + RAG Context + Producto]
         ↓
  JSON → {hs_code, confianza, razonamiento}
```

---

## 🎯 Lógica de Riesgo (PDR — Sección 2.3)

| Condición | Nivel | Acción |
| :--- | :---: | :--- |
| NIT en Listado Ficticios DIAN | 🔴 **ALTO** | Bloquear pago + alerta inmediata |
| BDME en mora **o** Facturador inactivo | 🟠 **MEDIO** | Revisar con asesor tributario |
| Consulta BDME falló/indeterminada | 🟣 **REVISAR** | Verificar manualmente |
| Sin alertas | 🟢 **BAJO** | Proveedor verificado |

> ⚠️ La lógica de riesgo es dictaminada **exclusivamente por el backend** (`calculate_risk()` en `src/report_engine.py`). El frontend nunca recalcula el riesgo localmente.

---

## ⚙️ Instalación y Ejecución

**1️⃣ Entorno**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2️⃣ Modelo IA Local (Ollama)**
```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

**3️⃣ Servidor API**
```bash
python api/main.py
# Swagger: http://localhost:8000/docs
```

**4️⃣ Abrir Interfaces**
- `dashboard.html` — Auditoría masiva de NITs
- `clasificador.html` — Clasificación arancelaria IA

---

## 🧩 Estado del Proyecto (MVP)

| Componente | Estado |
| :---: | :---: |
| 🚀 **API FastAPI + Endpoints** | ✅ |
| 🧠 **Clasificador IA RAG (qwen2.5)** | ✅ |
| 🔍 **Auditor NITs (DIAN + BDME)** | ✅ |
| 📄 **Reporte PDF con Razonamiento IA** | ✅ |
| 📊 **Reporte Excel con Colores** | ✅ |
| 🎨 **Dashboard Dark Theme B2B** | ✅ |
| 🔢 **Compatibilidad Universal (XLS/XLSX/CSV/CSV-in-Excel)** | ✅ |
| ⚡ **Aceleración CUDA RTX 3050** | ✅ |

---

## 👥 Autores

| Integrante | Rol |
| :--- | :--- |
| 👨‍💻 **Santiago Parra** | Arquitectura, Lógica de Riesgos, PDR y Dirección |
| 🤖 **Antigravity AI** | Implementación Backend/Frontend, RAG, Testing |

---

## 📄 Licencia

Distribuido bajo licencia **MIT**. Libre para uso privado y comercial con atribución a los autores originales.
