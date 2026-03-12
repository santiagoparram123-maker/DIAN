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
  <img src="https://img.shields.io/badge/AI-OLLAMA_QWEN-8A2BE2?style=for-the-badge&logo=meta&logoColor=white">
</p>

---

## 🧭 Descripción General

El **Auditor de Terceros y Cumplimiento DIAN** es un sistema Micro-SaaS B2B desarrollado para automatizar la auditoría de riesgos tributarios en proveedores de empresas.
El propósito del trabajo es aplicar técnicas de cruce de bases de datos, web scraping avanzado y normalización de textos, tomando como referencia fuentes gubernamentales como el **Listado de Proveedores Ficticios de la DIAN** y el **Boletín de Deudores Morosos del Estado (BDME) del CHIP**.

Además, incluye un módulo de **Auto-Clasificación Arancelaria Masiva** impulsado por IA local (`qwen2.5-coder:7b` vía Ollama), diseñado para agencias de aduanas que necesitan asignar automáticamente partidas arancelarias a catálogos enteros de productos importados a Colombia, reduciendo drásticamente el tiempo de clasificación manual.

Este repositorio contiene la **estructura completa del proyecto**, archivos base, scripts modulares, y una interfaz de usuario (*Dashboard*) preparados para su ejecución y despliegue local.

> 💡 *El proyecto se encuentra finalizado en el alcance del MVP. Puede ser empaquetado como API o servirse directamente vía web scripts interactivos.*

---

## 📂 Estructura del Proyecto

```text
DIAN_Auditor_B2B
┣ 📂 data
┃ ┣ 📜 dian_ficticios.parquet → Caché base limpia de DIAN
┃ ┣ 📜 bdme_cache.parquet → Caché temporal (30 días) para BDME
┃ ┗ 📜 catalogo_ejemplo.csv → Datos de prueba para clasificación IA
┣ 📂 outputs
┃ ┗ 📜 reporte_cumplimiento_...xlsx → Reportes y métricas generadas
┣ 📂 src
┃ ┣ 📜 bdme_scraper.py → Motor Selenium para CHIP/BDME
┃ ┣ 📜 dian_processor.py → Limpieza de base DIAN Excel
┃ ┣ 📜 report_engine.py → Calculador de matriz de riesgo e inyector Excel
┃ ┣ 📜 clasificador.py → Clasificador Arancelario IA (Ollama)
┃ ┗ 📜 utils.py → Utilidades de normalización NIT
┣ 📂 tests
┃ ┗ 📜 test_...py → Pruebas unitarias para pytest
┣ 📜 Proveedores-Ficticios-16022026.xlsx → Archivo maestro original
┣ 📜 dashboard.html → UI Interactiva Simulada y Panel B2B
┣ 📜 clasificador.html → UI del Auto-Clasificador IA (Dark Mode)
┣ 📜 requirements.txt → Dependencias de Python
┣ 📜 .env.example → Configuración de claves (Template)
┗ 📜 README.md → Este documento 🔥
```

---

## 💻 Tecnologías y Lenguajes Utilizados

| Tecnología | Descripción | Emoji |
| :--- | :--- | :---: |
| **Python 3.10+** | Lenguaje principal para backend y scraping | ⚙️ |
| **Ollama / Qwen** | IA local asíncrona para clasificación arancelaria masiva | 🧠 |
| **Selenium WebDriver** | Automatización web Headless para BDME (CHIP) | 🤖 |
| **Pandas / PyArrow** | Análisis, validación y exportación de datos (Excel/Parquet/CSV) | 📊 |
| **HTML / CSS / JS Vanilla** | Diseño de interfaz premium Micro-SaaS B2B | 🎨 |
| **Pytest** | Entorno para configuración de pruebas unitarias | 🧪 |
| **Git + VS Code** | Control de versiones y entorno de desarrollo | 🚀 |

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

## ⚙️ Cómo Ejecutar el Proyecto

**1️⃣ Clonar el repositorio**

```bash
git clone https://github.com/usuario/DIAN_Auditor_B2B.git
cd DIAN_Auditor_B2B
```

**2️⃣ Crear y activar un entorno virtual**

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

**3️⃣ Instalar dependencias requeridas**

```bash
pip install -r requirements.txt
```

**4️⃣ Requisitos para el Módulo IA (Opcional, si usas `clasificador.py`)**

Asegúrate de tener [Ollama](https://ollama.com/) instalado en tu sistema local.
```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

**5️⃣ Ejecutar pruebas o abrir interfaz**

```bash
# Ejecutar pipeline completo de cumplimiento en terminal
python src/report_engine.py

# Ejecutar el clasificador arancelario masivo en terminal
python src/clasificador.py data/catalogo_ejemplo.csv

# Ejecutar el suite unitario
pytest tests/
```
*(Para verificar la UI, abre `dashboard.html` o `clasificador.html` en tu navegador favorito)*

---

## 🧩 Estado Actual del Proyecto

| Componente | Descripción | Estado |
| :---: | :--- | :---: |
| 📂 **Estructura base del proyecto** | Setup del entorno, `.env` y requerimientos | ✅ Completo |
| 🗃️ **Módulo 1: Procesador DIAN** | Extracción ETL de "Proveedores Ficticios" | ✅ Completo |
| 🤖 **Módulo 2: Scraper BDME** | Minería de morosidad con Selenium y JSF | ✅ Completo |
| 📈 **Módulo 3: Motor de Reportes** | Matriz de riesgo tributario en Excel multicapa | ✅ Completo |
| 🧠 **Módulo 4: Clasificador IA** | Asignación automática de HS Codes con Qwen2.5 vía Ollama | ✅ Completo |
| 🎨 **Dashboard Web (UI)** | Panel mock de progreso premium sin librerías externas | ✅ Completo |
| 📄 **Documentación e integraciones** | Readme, git init y walkthrough final | ✅ Completo |

---

## 👥 Autores

| Integrante | Rol |
| :--- | :--- | 
| 👨‍💻 **Santiago Parra** | Diseño Arquitectónico, Lógica de Riesgos y Documentación |
| 🤖 **Antigravity AI Assistant** | Implementación de Código, Testing y Construcción de Frontend / Backend |

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Eres libre de usarlo, modificarlo y distribuirlo de forma privada o comercial, siempre que se mantenga el reconocimiento a sus autores originales.
