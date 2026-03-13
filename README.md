<h1 align="center"> 📊 Auditor de Terceros y Cumplimiento DIAN — B2B 🧠 </h1>

<p align="center">
  <b>Automatización de Análisis de Riesgo Tributario con Python y Selenium</b><br>
  <i>Micro-SaaS B2B — Inteligencia Financiera y Cumplimiento</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/STATUS-COMPLETO-007EC6?style=for-the-badge&logo=github">
  <img src="https://img.shields.io/badge/PYTHON-3.10+-F2C63C?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/UI-HTML_Vanilla-E34F26?style=for-the-badge&logo=html5&logoColor=white">
  <img src="https://img.shields.io/badge/LIBRER%C3%8DA-SELENIUM-43B02A?style=for-the-badge&logo=selenium&logoColor=white">
  <img src="https://img.shields.io/badge/AI-OLLAMA_PHI-8A2BE2?style=for-the-badge&logo=meta&logoColor=white">
</p>

---

## 🧭 Descripción General

El **Auditor de Terceros y Cumplimiento DIAN** es un sistema Micro-SaaS B2B desarrollado para automatizar la auditoría de riesgos tributarios en proveedores de empresas. Soporta archivos **CSV y Excel (XLSX/XLS)**.
El propósito del trabajo es aplicar técnicas de cruce de bases de datos, web scraping avanzado y normalización de textos, tomando como referencia fuentes gubernamentales como el **Listado de Proveedores Ficticios de la DIAN** y el **Boletín de Deudores Morosos del Estado (BDME) del CHIP**.

Además, incluye un módulo de **Auto-Clasificación Arancelaria Masiva** impulsado por IA local (`phi4:latest` vía Ollama), diseñado para agencias de aduanas que necesitan asignar automáticamente partidas arancelarias a catálogos enteros de productos importados a Colombia (desde **Excel o CSV**), reduciendo drásticamente el tiempo de clasificación manual.

Este repositorio contiene la **estructura completa del proyecto**, archivos base, scripts modulares, y una interfaz de usuario (*Dashboard*) preparados para su ejecución y despliegue local.

> 💡 *El proyecto se encuentra finalizado en el alcance del MVP. Puede ser empaquetado como API o servirse directamente vía web scripts interactivos.*

---

## 📂 Estructura del Proyecto

```text
DIAN_Auditor_B2B
┣ 📂 api                    # Capa de Interoperabilidad (FastAPI)
┃ ┗ 📜 main.py              # Endpoints: /api/auditar-terceros, /api/clasificar-masivo
┣ 📂 data                   # Gestión de datos y datasets
┃ ┣ 📂 raw                  # Archivos maestros originales (Proveedores-Ficticios...)
┃ ┣ 📂 samples              # Archivos de prueba para demostraciones
┃ ┣ 📜 processed            # Parquet files procesados
┃ ┣ 📜 historico_dian.csv   # Dataset para RAG (Clasificador IA)
┃ ┣ 📜 dian_ficticios.parquet
┃ ┗ 📜 bdme_cache.parquet
┣ 📂 docs                   # Documentación técnica y requerimientos
┣ 📂 logs                   # Trazas y salidas de ejecución
┣ 📂 scripts                # Scripts de depuración y herramientas internas
┣ 📂 src                    # Núcleo de la lógica de negocio (Core)
┃ ┣ 📜 bdme_scraper.py      # Motor Selenium para deudores (CHIP)
┃ ┣ 📜 dian_processor.py    # Procesador de base DIAN con Polars
┃ ┣ 📜 report_engine.py     # Generador de reportes de cumplimiento
┃ ┣ 📜 clasificador.py      # Clasificador IA con RAG (Phi / SentenceTransformers)
┃ ┗ 📜 utils.py             # Utilidades y normalización
┣ 📂 tests                  # Pruebas automatizadas (Pytest)
┣ 📜 dashboard.html         # Portal de Auditoría (Frontend)
┣ 📜 clasificador.html      # Portal de Clasificación IA (Frontend)
┣ 📜 requirements.txt       # Dependencias del proyecto
┗ 📜 README.md              # Guía principal del sistema
```

---

## 💻 Tecnologías y Lenguajes Utilizados

| Tecnología | Descripción | Emoji |
| :--- | :--- | :---: |
| **Python 3.10+** | Lenguaje principal (Backend / Scraping / ML) | ⚙️ |
| **FastAPI** | Orquestador asíncrono y documentación Swagger | 🚀 |
| **Ollama / Phi-4** | IA local para clasificación (Reasoning Engine) | 🧠 |
| **FAISS / SentenceTransformers** | Arquitectura RAG (Retrieval-Augmented Generation) | 🔍 |
| **Polars** | Procesamiento de datos ultrarrápido out-of-core | ⚡ |
| **Selenium WebDriver** | Automatización web para consultas gubernamentales | 🤖 |

---

## 🧠 Arquitectura RAG (Retrieval-Augmented Generation)

Para evitar alucinaciones en la clasificación arancelaria, el sistema implementa un pipeline de RAG:
1. **Vectorización**: Las descripciones históricas de la DIAN se convierten en vectores densos usando `all-MiniLM-L6-v2`.
2. **Recuperación**: Al recibir un producto nuevo, se buscan los Top-3 ejemplos más similares en la base vectorial local.
3. **Inyección de Contexto**: Se envía el producto + ejemplos históricos al modelo `phi4` para una decisión informada y determinística.

---

## ⚙️ Cómo Ejecutar el Proyecto

**1️⃣ Instalación de Entorno**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2️⃣ Configuración de IA Local**
```bash
ollama run phi4
```

**3️⃣ Iniciar Servidor API**
```bash
python api/main.py
# Visita http://localhost:8000/docs para el Swagger automático
```

**4️⃣ Ejecutar Pruebas**
```bash
pytest tests/
```

---

## 🧠 Objetivos del Sistema

- ✅ Normalizar cadenas de texto complejas (NITs) bajo reglas estándar de 9 dígitos.
- ✅ Ingestar y cachear eficientemente archivos masivos excel de la DIAN a formato .parquet.
- ✅ Implementar un Scraper Selenium asíncrono y resiliente con límite por lote (Rate Limit).
- ✅ Unificar bases de datos para predecir Niveles de Riesgo (ALTO, MEDIO, REVISAR, BAJO).
- ✅ Generar reportes automatizados en Excel divididos en "Resumen" y "Detalle" formateados condicionalmente.
- ✅ **NUEVO:** Clasificar automáticamente catálogos de importación usando IA Local (Ollama) evaluando texto no estructurado y asignando HS Codes con niveles de confianza.
- ✅ Mantener una estructura de proyecto profesional, modularizada y reproducible.

---

## 🧩 Estado Actual del Proyecto

| Componente | Estado |
| :---: | :---: |
| 📂 **Estructura Organizada** | ✅ |
| 🚀 **API FastAPI Finalizada** | ✅ |
| 🧠 **IA Clasificadora con RAG** | ✅ |
| 🤖 **Scraper BDME Resiliente** | ✅ |
| 📈 **Generación de Reportes Excel** | ✅ |
| 🎨 **Interfaz Dashboard B2B** | ✅ |

---

## 👥 Autores

| Integrante | Rol |
| :--- | :--- | 
| 👨‍💻 **Santiago Parra** | Diseño Arquitectónico, Lógica de Riesgos y Documentación |
| 🤖 **Antigravity AI Assistant** | Implementación de Código, Testing y Construcción de Frontend / Backend |

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Eres libre de usarlo, modificarlo y distribuirlo de forma privada o comercial, siempre que se mantenga el reconocimiento a sus autores originales.
