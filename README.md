# Research Buddy — Backend (MVP)

Research Buddy is a modular AI backend that streamlines literature review with classification, keyword extraction, and summarization services. Built on FastAPI, it is designed for clean extension and model comparability and can evolve into a conversational RAG assistant.

---

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
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
│   └── routes/
│       └── predict.py         # /predict, /keywords, /summary, /health
│
├── data/                      # Models, tokenizers, vectorizers (not tracked)
│   ├── logistic_model.pkl
│   ├── sci_model.pkl
│   └── bert_model/...
│
├── requirements.txt
└── run.py                     # Uvicorn launcher
```

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

## API Reference

| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/predict` | POST | Classify research abstracts |
| `/api/keywords` | POST | Extract keywords |
| `/api/summary` | POST | Generate summaries |
| `/api/health` | GET | Health check |

Example request:
```json
{
  "text": "This paper introduces a transformer-based model for biomedical literature classification.",
  "model": "bert"
}
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

## Author

**Nur A. Jaman (Turjo)**  
AI & EdTech Innovator | Full-Stack Engineer  
🌐 [https://turjo-jaman.com](https://turjo-jaman.com)
