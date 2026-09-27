# 🇮🇳 National Material Harmonization Engine (SIH 26099)
### *AI-Powered Centralized National Material Coding (CNMC) Across CPSEs*

[![Smart India Hackathon](https://img.shields.io/badge/SIH_2024-Problem_Statement_26099-orange.svg)](https://sih.gov.in/)
[![Ministry](https://img.shields.io/badge/Ministry-Ministry_of_Petroleum_%26_Natural_Gas-blue.svg)](https://mopng.gov.in/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Problem Statement Overview (SIH 26099)
* **Problem ID**: SIH 26099
* **Organization**: Ministry of Petroleum & Natural Gas (MoP&NG)
* **Theme**: Smart Automation & Supply Chain Optimization
* **Vision**: *"One Nation, One Material Identity"*

Major Central Public Sector Enterprises (**ONGC, IOCL, GAIL, SAIL, HPCL, BPCL**) maintain fragmented material master catalogs developed independently over decades. The identical physical spare part or industrial component is logged under dissimilar item codes, naming conventions, and units across sister PSUs.

This fragmentation leads to:
1. **Loss of Bulk Procurement Power**: Billions in lost volume discounts due to isolated tenders.
2. **Idle Capital & Dead Stock**: Inability to share emergency spare parts between neighboring CPSE refineries and plants.
3. **Catastrophic Safety Risks**: Accidental substitution of incompatible components (e.g., Class 150 vs Class 600 valves).

---

## 💡 The Solution: Centralized National Material Coding (CNMC)
The **National Material Harmonization Engine** is a high-precision, 5-tier platform that combines **neural semantic embeddings** with a **deterministic engineering safety gate** to standardize, match, and deduplicate cross-CPSE material catalogs into unified **CNMC** identities with 100% auditability.

```
Multi-CPSE ERP Catalogs (ONGC, IOCL, GAIL, SAIL)
                      │
                      ▼
 ┌──────────────────────────────────────────────┐
 │ TIER 1: Catalog Normalization & Material DNA │ ➔ Extract Specs, UoM, Dimensions
 └──────────────────────┬───────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ TIER 2: Hybrid AI Matcher & Safety Gate      │ ➔ Dense Embeddings + ASME B16.5 Safety Check
 └──────────────────────┬───────────────────────┘
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
     [Confidence ≥ 85%]     [60% - 84% Ambiguous]
      Auto-Linked Pass             │
             │                     ▼
             │       ┌───────────────────────────────┐
             │       │ TIER 3: Human Review Queue    │ ➔ 1-Click Approval / Rejection
             │       └─────────────┬─────────────────┘
             │                     │
             └──────────┬──────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ TIER 4: CNMC Registry & Immutable Audit Trail│ ➔ CVC / CAG Compliant Traceability
 └──────────────────────┬───────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ TIER 5: Executive Dashboard & Savings Model  │ ➔ Real-time ROI & Analytics
 └──────────────────────────────────────────────┘
```

---

## ✨ Key Features & Innovations

### 1. 🧬 Parameter-Driven Material DNA Extraction
Converts unstructured, ambiguous ERP catalog descriptions into standardized canonical parameter vectors:
* **Item Category & Subtype** (e.g., `GATE VALVE`, `WELD NECK FLANGE`, `SPIRAL GASKET`)
* **Nominal Size & Dimensions** (e.g., `DN100 / 4"`, `Sch 40`)
* **Pressure Rating & Class** (e.g., `Class 150#`, `Class 600#`, `PN16`)
* **Material Metallurgy** (e.g., `ASTM A105`, `ASTM A106 Gr B`, `SS316`)
* **Facing & Standard** (e.g., `RF`, `RTJ`, `ASME B16.5`, `ASME B16.20`)

### 2. 🤖 Hybrid Neural + Technical Matching Engine
Evaluates candidate pairs using a weighted tripartite confidence algorithm:
$$\text{Score} = 0.50 \times \text{Semantic Embedding Similarity} + 0.30 \times \text{Spec DNA Match} + 0.20 \times \text{UoM Compatibility}$$
* Powered by `sentence-transformers` (`all-MiniLM-L6-v2`) dense vector representations.
* Token n-gram normalization handles CPSE-specific abbreviations and syntax variations.

### 3. 🛡️ Deterministic Engineering Safety Gate
Prevents catastrophic false-positive merges:
* If pressure class conflicts (`CL150` vs `CL600`), diameter mismatches, or metallurgy discrepancies are detected, the Safety Gate **blocks the merge unconditionally** (`HTTP 400`), overriding high text similarity.

### 4. 👥 Human-in-the-Loop Review Workspace
* Provides procurement leads with interactive visual attribute comparisons, conflict flags, and 1-click candidate approval.
* Approved items instantly graduate to the **CNMC Registry** and are automatically removed from the pending review queue.

### 5. 🏛️ Immutable Governance & CAG/CVC Audit Trail
* Logs every decision (`auto_linked`, `human_approved`, `human_rejected`, `safety_gate_blocked`) with officer credentials, timestamps, and JSON snapshots.
* 1-click **CSV Audit Export** ready for statutory audits (CAG) and Central Vigilance Commission (CVC) compliance.

### 6. 💰 Financial ROI & Savings Simulation
* Calculates real-time projected procurement savings based on cross-CPSE duplicate rates and volume discount negotiation bands.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| **AI / NLP** | PyTorch, `sentence-transformers` (`all-MiniLM-L6-v2`), Scikit-learn |
| **Persistence** | SQLite / PostgreSQL, SQLAlchemy ORM |
| **Frontend UI** | HTML5, Modern Vanilla JavaScript, Tailwind CSS, Lucide Icons, Chart.js |
| **Engineering Rules** | ASME B16.5, ASME B16.20, ASTM A105/A106 standards |

---

## 📁 Repository Structure

```text
├── src/
│   ├── app.py                     # Main FastAPI server entry point
│   ├── ingestion/                 # Tier 1: CSV parser & Material DNA normalizer
│   ├── matching/                  # Tier 2: AI embedding model & Safety Gate rules
│   ├── review_api/                # Tier 3: Review Queue API & Decision Handlers
│   ├── persistence/               # Tier 4: CNMC database models, registry & audit logs
│   └── dashboard/
│       ├── routes.py              # Tier 5: Dashboard & metrics routes
│       └── static/
│           └── index.html         # Unified single-page dashboard application
├── data/
│   ├── raw/                       # CPSE catalog extracts (ONGC, IOCL, GAIL, SAIL)
│   └── processed/                 # Standardized JSONL outputs & match files
├── docs/                          # Comprehensive architecture & Tier specification docs
├── requirements.txt               # Production Python dependencies
└── README.md                      # Project documentation
```

---

## 🚀 Quickstart & Local Installation

### Prerequisites
* **Python 3.11+** installed
* **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/Naresh63-hub/national-material-harmonization-engine.git
cd national-material-harmonization-engine
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the Engine & Dashboard
```bash
python -m uvicorn src.app:app --host 127.0.0.1 --port 8001 --reload
```

### 5. Open in Your Browser
Open 👉 **[http://127.0.0.1:8001/](http://127.0.0.1:8001/)**

---

## ⚡ Live Demo Scenarios

Within the **Review Queue** tab, test the 3 pre-configured scenarios:
1. 🟢 **Scenario 1: Valid Match (Safety Pass)**
   * *Example*: Seamless Carbon Steel Pipes across ONGC & IOCL.
   * *Result*: High AI confidence + full parameter compatibility $\rightarrow$ Approved to CNMC.
2. 🔴 **Scenario 2: Critical Conflict (Safety Block)**
   * *Example*: Class 150 vs Class 600 Gate Valves.
   * *Result*: Text looks similar, but ASME B16.5 Safety Gate flags pressure mismatch $\rightarrow$ Blocked from consolidation.
3. 🟡 **Scenario 3: Ambiguous Candidate (Human Review)**
   * *Example*: Spiral Wound Gaskets with partial spec alignment.
   * *Result*: Routed to Human-in-the-Loop workspace for expert verification.

---

## 📜 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | Platform KPIs, duplicate %, and financial savings summary |
| `GET` | `/api/pending-reviews` | Candidate matches needing human validation or safety audit |
| `POST` | `/api/review-decision` | Submit human approval / rejection and mint CNMC records |
| `POST` | `/api/batch-approve` | Bulk approve all candidate pairs with confidence $\ge 70\%$ |
| `GET` | `/api/cnmc` | Full Centralized National Material Code Registry |
| `GET` | `/api/audit-trail` | Immutable statutory governance logs |
| `GET` | `/api/audit-trail/export` | One-click CSV audit export for CAG / CVC inspectors |

---

## 🏆 Smart India Hackathon 2024
* **Team**: Popeye
* **Problem Statement**: SIH 26099 — AI-Driven Material Code Standardization Across CPSEs
* **Target Beneficiaries**: MoP&NG, ONGC, IOCL, GAIL, SAIL, HPCL, BPCL, GeM, DPE

---

## 📄 License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
