# Research Buddy — Backend (MVP)

Research Buddy is a modular AI backend that streamlines literature review with classification, keyword extraction, and summarization services. Built on FastAPI, it is designed for clean extension and model comparability and can evolve into a conversational RAG assistant.

---

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Project-Structure](#project-structure)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Models](#models)
- [Development](#development)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Security Notes](#security-notes)
- [License](#license)
- [Author](#author)

---

## Features
- Abstract classification with interchangeable models (classical ML, neural, transformers).
- Keyword extraction (KeyBERT and optional LLM-based).
- Summarization (extractive and optional LLM-based).
- Modular loader to add/replace models by dropping files under `data/`.
- Clean, typed FastAPI endpoints with Pydantic schemas.

---

## Architecture
- **Framework:** FastAPI + Uvicorn
- **Core Modules:** `models/loader.py` (model loading), `models/predictor.py` (inference)
- **Contracts:** Pydantic request/response in `schemas/`
- **Routing:** All public routes under `app/routes/`
- **Extensibility:** Add new models without changing route contracts by updating `loader.py` and `predictor.py`

---

## Project Structure
```
research_buddy_backend/
│
├── app/
│   ├── main.py                # FastAPI entry point
│   ├── config.py              # Paths, feature flags, env accessors
│   ├── models/
│   │   ├── loader.py          # Model & vectorizer loading
│   │   └── predictor.py       # Inference logic
│   ├── schemas/
│   │   └── predict.py         # Pydantic I/O schemas
│   ├── routes/
│   │   └── predict.py         # /predict, /keywords, /summary, /health
│   ├── Data/                  # Internal assets for classification and NLP models
│   └── nltk_data/             # NLTK tokenizers, corpora, and linguistic utilities
│
├── data/                      # Models, tokenizers, vectorizers (not tracked)
│   ├── logistic_model.pkl
│   ├── sci_model.pkl
│   └── bert_model/...
│
├── requirements.txt
└── run.py                     # Uvicorn launcher
```

> **Note:**  
> The `app/Data/` and `app/nltk_data/` folders contain important resources that support text preprocessing and NLP pipelines.  
> These directories are not publicly distributed. To access them or contribute updates, please contact the project owner.

---

## Quickstart

### 1) Local (venv)
```bash
git clone https://github.com/Tj-jm/research-buddy-backend.git
cd research-buddy-backend

python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
# venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env   # then edit as needed

python run.py
# http://localhost:8000 (OpenAPI at /docs)
```

### 2) Docker
```bash
docker build -t research-buddy-backend .
docker run --rm -p 8000:8000   -v $(pwd)/data:/app/data   --env-file .env   research-buddy-backend
```

---

## Configuration

Provide environment variables in `.env`:

```env
# Optional: path overrides (defaults point to ./data)
MODEL_PATH=data/
LOG_LEVEL=info
ENABLE_SUMMARIZER=true
```



---

## Models

| Type | Implementations |
|------|------------------|
| Classical ML | Logistic Regression, SVM, Naive Bayes |
| Neural | Feedforward NN, LSTM, CNN |
| Transformer | DistilBERT, SciBERT |
| Keyword | KeyBERT, Gemini LLM |
| Summarizer | BART, Gemini Hybrid |

---

## Development
```bash
# Run formatters and linters
black app
flake8 app
pytest
```

---

## Roadmap
- [ ] Add PDF parsing endpoint
- [ ] Integrate RAG chat mode
- [ ] Add Redis-based caching
- [ ] Docker Compose setup for frontend-backend integration

---

## Security Notes
This backend is designed for educational and demonstration purposes.  
It does not store user data and assumes trusted inputs in MVP state.

---

## License
Proprietary — for portfolio and educational demonstration only.  
Unauthorized redistribution or commercial use is prohibited.

---

## Reference White Paper
Read the full Research Buddy white paper here:  
🔗 [https://turjo-ml-dl.turjo-jaman.com/research_buddy.html](https://turjo-ml-dl.turjo-jaman.com/research_buddy.html)

---

## Author

**Nur A. Jaman (Turjo)**  
AI & EdTech Innovator | Full-Stack Engineer  
🌐 [https://turjo-jaman.com](https://turjo-jaman.com)


---

## 🧩 API Reference

### 🔮 Prediction API (`/api/predict`)
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/predict` | **POST** | Classifies research abstracts using the selected ML or transformer model (`model_name`: "ALL", "bert", etc.). |
| `/api/predict-pdf` | **POST** | Extracts text from a PDF file and performs classification with the chosen model. |
| `/api/extract_keywords_pdf` | **POST** | Extracts top keywords from the first two pages of a PDF using KeyBERT. |
| `/api/extract_keywords_text` | **POST** | Extracts keywords from a raw abstract text via KeyBERT. |
| `/api/extract_keywords_gemini` | **POST** | Extracts context-aware keywords using Gemini LLM. |
| `/api/summarize` | **POST** | Summarizes abstracts using either Gemini or BART summarization models. |

**Example Request**
```json
{
  "abstract": "This paper introduces a transformer-based model for biomedical literature classification.",
  "model_name": "bert"
}
```
**Example Response**
```json
{
  "predicted_label": "Computer Science",
  "confidence": 0.94
}
```

---

### 👤 Authentication API (`/api/auth`)
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/signup` | **POST** | Registers a new user and returns a JWT token stored in an HttpOnly cookie. |
| `/api/login` | **POST** | Authenticates user credentials and issues a JWT cookie. |
| `/api/logout` | **POST** | Logs out the user by deleting the token cookie. |
| `/api/me` | **GET** | Returns the authenticated user’s email from the JWT token. |

**Note:**  
All authentication routes use cookie-based JWTs and integrate with the middleware in `app/middlewares/user_protect.py`.

---

### 📚 Dashboard API (`/api/dashboard`)
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/dashboard/papers` | **POST** | Uploads a research paper (PDF) to Backblaze B2 and stores metadata in MongoDB. |
| `/api/dashboard/papers` | **GET** | Lists all uploaded papers for the authenticated user (pagination, search, filters supported). |
| `/api/dashboard/papers/{paper_id}` | **GET** | Retrieves details for a single paper. |
| `/api/dashboard/papers/{paper_id}` | **PUT** | Updates paper information (title, abstract, summary, etc.). |
| `/api/dashboard/papers/{paper_id}` | **DELETE** | Deletes both the file from B2 and its database record. |
| `/api/dashboard/papers/{paper_id}/download` | **GET** | Downloads a paper from B2 storage. |
| `/api/dashboard/papers/{paper_id}/favorite` | **PUT** | Marks or unmarks a paper as a favorite. |

**Protected Routes:** All `/dashboard/*` endpoints are protected by the `userProtect` middleware.

---

### 🧑‍🔬 Faculty Scraper Agent API (`/api/faculty`)
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/faculty/scrape` | **POST** | Launches an adaptive or deep faculty scraping engine for a given university/faculty page. Returns Excel file and summary stats. |
| `/api/faculty/download/{filename}` | **GET** | Downloads a generated Excel file containing scraped faculty data. |
| `/api/faculty/progress` | **GET** | Streams scraping progress via Server-Sent Events (SSE). |

**Engines Supported:**  
- Adaptive Faculty Scraper (default)  
- Enhanced Deep Faculty Scraper (for large-scale or structured university portals)

---

### 🧠 Faculty Scrape Database API (`/api/faculty-scrape-db`)
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/faculty-scrape-db/save` | **POST** | Saves a completed scraping session result to the database. |
| `/api/faculty-scrape-db/list` | **GET** | Returns paginated list of previously saved scrape sessions. |
| `/api/faculty-scrape-db/{scrape_id}` | **GET** | Retrieves a specific scraping record by ID. |
| `/api/faculty-scrape-db/{scrape_id}` | **DELETE** | Permanently deletes a scraping record. |

---

### 🧭 Root Endpoint
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/` | **GET** | Returns `{ "message": "Research Buddy Backend is Running" }` |
