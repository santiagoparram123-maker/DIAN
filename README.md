<h1 align="center">📊 B2B Customs Risk Auditor — AAA Agency of AI 🧠</h1>

<p align="center">
  <b>Tax Due Diligence Engine · Fictitious Suppliers Prevention · AI Tariff Classification</b><br>
  <i>B2B Micro-SaaS — DIAN Compliance · BDME · Electronic Billers</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/STATUS-PRODUCTION_MVP-00C851?style=for-the-badge&logo=github">
  <img src="https://img.shields.io/badge/PYTHON-3.10+-F2C63C?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/API-FASTAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/AI-OLLAMA_QWEN2.5-8A2BE2?style=for-the-badge&logo=meta&logoColor=white">
  <img src="https://img.shields.io/badge/RAG-FAISS_+_MiniLM-FF6B35?style=for-the-badge">
  <img src="https://img.shields.io/badge/HARDWARE-CUDA_RTX_3050-76B900?style=for-the-badge&logo=nvidia&logoColor=white">
</p>

---

## 🧭 Overview

The **B2B Customs Risk Auditor** is a core tool of the **AAA Agency of AI**, designed to automate tax risk auditing and tariff classification for suppliers and imports in Colombia.

It operates as a **FastAPI microservice** that combines three main engines:

1. **Tax Due Diligence Engine** — Cross-references NITs (Tax Identification Numbers) against the Fictitious Suppliers List (DIAN), the BDME (Defaulting Debtors Bulletin / CHIP), and the Electronic Billers database, generating risk matrices (`HIGH` / `MEDIUM` / `REVIEW` / `LOW`) according to the system's PDR.
2. **AI Tariff Classifier** — Automatically assigns HS Code headings to import catalogs using `qwen2.5-coder:7b` via Ollama with a CUDA-accelerated RAG (Retrieval-Augmented Generation) pipeline.
3. **Report Generator** — Produces Excel reports with conditional color formatting and PDFs containing the AI model's reasoning.

> 💡 **Value Proposition:** It's not just "automation" — it's **fine prevention and corporate asset protection**. The ideal client (freight forwarders, e-commerce, companies with many suppliers) already feels the pain and has the budget to solve it.

---

## 📂 Project Structure

```text
DIAN_Auditor_B2B
┣ 📂 api
┃ ┗ 📜 main.py              # FastAPI Microservice (audit-json, mass-classify, generate-pdf-report)
┣ 📂 data
┃ ┣ 📂 raw                  # Proveedores-Ficticios-DIAN.xlsx (official source)
┃ ┣ 📂 samples              # Test files (test_01/02/03)
┃ ┣ 📜 historico_dian.csv   # Knowledge base for RAG
┃ ┣ 📜 dian_ficticios.parquet
┃ ┗ 📜 bdme_cache.parquet
┣ 📂 docs
┃ ┗ 📜 PDR_Auditor_DIAN.docx  # Project Definition Record (Architecture + Guardrails)
┣ 📂 outputs               # Generated reports (Excel + PDF)
┣ 📂 src                   # Business core (Core — DO NOT modify without PDR)
┃ ┣ 📜 clasificador.py     # RAG + Ollama qwen2.5-coder:7b + CUDA + LRU Cache
┃ ┣ 📜 report_engine.py    # NIT audit engine with PDR risk matrix
┃ ┣ 📜 dian_processor.py   # Polars processor for DIAN database
┃ ┣ 📜 bdme_scraper.py     # BDME Scraper (CHIP)
┃ ┗ 📜 utils.py            # normalize_nit() — 9 digits, PDR primary key
┣ 📜 dashboard.html        # Third-Party Audit Portal (B2B Dark Theme)
┣ 📜 clasificador.html     # Mass AI Classification Portal
┣ 📜 requirements.txt
┗ 📜 README.md
```

---

## 💻 Tech Stack

| Technology | Description |
| :--- | :--- |
| **Python 3.10+** | Backend, data processing, and ML |
| **FastAPI + Uvicorn** | Asynchronous API with automatic Swagger documentation |
| **Ollama / qwen2.5-coder:7b** | Local AI model for tariff classification |
| **FAISS + SentenceTransformers** | RAG Pipeline — top_k=10, cosine similarity |
| **Polars + Pandas** | Out-of-core processing for massive databases |
| **CUDA (RTX 3050)** | GPU acceleration for embeddings and AI model |
| **fpdf2** | Professional PDF report generation with AI reasoning |
| **openpyxl + xlrd** | Universal Excel compatibility (XLS, XLSX, CSV-in-Excel) |
| **Selenium** | Resilient queries to BDME/CHIP |

---

## 🧠 RAG Pipeline — Tariff Classifier

```
CSV/XLSX Catalog → load_file()
         ↓ (magic bytes detection + CSV-in-Excel)
    pd.DataFrame (ID, DESCRIPTION)
         ↓
  SentenceTransformer.encode() [CUDA]
  + LRU Cache (maxsize=1000)
         ↓
  FAISS.search(top_k=10) → Similar DIAN examples
         ↓
  Ollama qwen2.5-coder:7b
  [System Prompt + RAG Context + Product]
         ↓
  JSON → {hs_code, confidence, reasoning}
```

---

## 🎯 Risk Logic (PDR — Section 2.3)

| Condition | Level | Action |
| :--- | :---: | :--- |
| NIT in DIAN Fictitious List | 🔴 **HIGH** | Block payment + immediate alert |
| BDME in default **or** inactive biller | 🟠 **MEDIUM** | Review with tax advisor |
| BDME query failed/indeterminate | 🟣 **REVIEW** | Verify manually |
| No alerts | 🟢 **LOW** | Verified supplier |

> ⚠️ The risk logic is dictated **exclusively by the backend** (`calculate_risk()` in `src/report_engine.py`). The frontend never recalculates the risk locally.

---

## ⚙️ Installation and Execution

**1️⃣ Environment**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2️⃣ Local AI Model (Ollama)**
```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

**3️⃣ API Server**
```bash
python api/main.py
# Swagger: http://localhost:8000/docs
```

**4️⃣ Open Interfaces**
- `dashboard.html` — Mass NIT auditing
- `clasificador.html` — AI tariff classification

---

## 🧩 Project Status (MVP)

| Component | Status |
| :---: | :---: |
| 🚀 **FastAPI API + Endpoints** | ✅ |
| 🧠 **RAG AI Classifier (qwen2.5)** | ✅ |
| 🔍 **NIT Auditor (DIAN + BDME)** | ✅ |
| 📄 **PDF Report with AI Reasoning** | ✅ |
| 📊 **Excel Report with Colors** | ✅ |
| 🎨 **B2B Dark Theme Dashboard** | ✅ |
| 🔢 **Universal Compatibility (XLS/XLSX/CSV/CSV-in-Excel)** | ✅ |
| ⚡ **CUDA RTX 3050 Acceleration** | ✅ |

---

## 👥 Authors

| Member | Role |
| :--- | :--- |
| 👨‍💻 **Santiago Parra** | Architecture, Risk Logic, PDR, and Direction |
| 🤖 **Antigravity AI** | Backend/Frontend Implementation, RAG, Testing |

---

## 📄 License

Distributed under the **MIT** license. Free for private and commercial use with attribution to the original authors.
