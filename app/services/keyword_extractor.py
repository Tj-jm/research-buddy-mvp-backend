from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import re
from google import genai
from google.genai import types
from typing import List
import requests
from app.config import GEMINI_API_KEY


client = genai.Client()


# Load once at module level
#kw_model = KeyBERT(model=SentenceTransformer("allenai/specter"))
kw_model = KeyBERT(model=SentenceTransformer("sentence-transformers/all-mpnet-base-v2"))
#kw_model = KeyBERT(model=SentenceTransformer("allenai/scibert_scivocab_uncased"))

# Bad keyword filters
def is_clean_keyword(kw: str) -> bool:
    if any(char.isdigit() for char in kw):
        return False
    if len(kw.split()) < 2:
        return False
    if re.search(r"(doi|http|@|copyright|cn|com|edu|org|gmail)", kw, re.IGNORECASE):
        return False
    if kw.lower() in {"introduction", "conclusion", "abstract", "figure"}:
        return False
    return True

def extract_keywords_keybert(text: str, top_n: int = 10, title: str = None):
    """
    Extract top N clean keywords from academic text using KeyBERT.
    Includes MMR-based diversity and optional title boosting.
    """

    if title:
        # Boost title terms by adding it twice
        text = f"{title}. {title}. {text}"

    raw_keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(2, 4),     # force multi-word phrases
        stop_words='english',
        use_mmr=True,
        diversity=0.6,                    # 0.5–0.7 is a good range
        top_n=max(30, top_n * 3)
    )

    

    filtered = [kw for kw, _ in raw_keywords if is_clean_keyword(kw)]
    return filtered[:top_n]
 

# def extract_keywords_keybert(text: str, top_n: int = 10, title: str = None):
#     """
#     Extract top N clean keywords from academic text using KeyBERT and SPECTER.
#     Includes MMR-based diversity and optional title boosting.
#     """

#     if title:
#         text = f"{title}. {text}"

#     raw_keywords = kw_model.extract_keywords(
#          text,
#         keyphrase_ngram_range=(1, 3),     # force multi-word
#         stop_words='english',
#         use_mmr=True,
#         diversity=0.6,                    # 0.5–0.7 is a good range
#         top_n=max(30, top_n * 3) 
#     )

#     filtered = [kw for kw, _ in raw_keywords if is_clean_keyword(kw)]
#     return filtered[:top_n]


#gemini keyword extractions

def extract_keywords_gemini(text: str, top_n: int = 10) -> List[str]:
    prompt = f"""
Extract the top {top_n} most relevant keywords or keyphrases from the following academic abstract.
Return only a clean, comma-separated list of keywords. No explanations.

Abstract:
{text}
"""
    try:
        response = client.models.generate_content(
            model="models/gemini-1.5-flash",  # Use 2.5 only if you’re enrolled in trusted tester
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_k=40,
                top_p=0.95,
            )
        )
        raw = response.text.strip()
        return [kw.strip() for kw in raw.split(",") if kw.strip()]

    except Exception as e:
        print("[Gemini Keyword Error]", e)
        return []