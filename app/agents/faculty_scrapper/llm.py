import os, json, httpx
from typing import List, Dict, Any
from loguru import logger

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

SYSTEM_PROMPT = """You are an information extraction assistant.
Given RAW PROFILE TEXT and its URL + university name, extract the following as a single JSON object with EXACT keys:

Professor Name, Designation, University Name, Email, Profile Link, Hook Point, Research Interests, Personal Website, Google Scholar, Bio, Source, Subject

Rules:
- Subject must be one of: "AI/ML", "Education & Leadership", "Data Science". Pick the closest based on research area.
- Do not invent emails or links. If unknown, return null.
- Hook Point: 1–2 sentence research focus in plain English.
- University Name: prefer explicit text; else infer from domain if obvious.
- Output valid JSON ONLY, no markdown or explanations.
"""

def _gemini_summarize(items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(GEMINI_MODEL)

    outputs = []
    for it in items:
        prompt = f"""{SYSTEM_PROMPT}

URL: {it['url']}
University (hint): {it.get('university','')}
RAW PROFILE TEXT:
{it['text']}
"""
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        # Gemini often returns JSON text directly
        try:
            data = json.loads(resp.candidates[0].content.parts[0].text)  # robust parse if needed
        except Exception:
            data = json.loads(resp.text)
        outputs.append(data)
    return outputs

def _ollama_summarize(items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    headers = {"Content-Type": "application/json"}
    outputs = []
    for it in items:
        prompt = f"""{SYSTEM_PROMPT}

URL: {it['url']}
University (hint): {it.get('university','')}
RAW PROFILE TEXT:
{it['text']}
"""
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": "Respond with pure JSON only."},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.2}
        }
        r = httpx.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        # Ollama streams by default; but /api/chat returns 'message' content
        content = r.json().get("message", {}).get("content", "")
        outputs.append(json.loads(content))
    return outputs

def summarize_batch(items: List[Dict[str, str]], provider_override: str | None = None) -> List[Dict[str, Any]]:
    provider = (provider_override or MODEL_PROVIDER).lower()
    logger.info(f"Summarizer using provider={provider}")
    if provider == "local":
        return _ollama_summarize(items)
    return _gemini_summarize(items)
