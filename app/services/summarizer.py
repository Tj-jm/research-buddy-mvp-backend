
from google import genai
from app.config import GEMINI_API_KEY
from transformers import pipeline
import logging
from google.genai import types
import textwrap
import os
# import nltk
import re

# Ensure cache goes to D drive
os.environ["TRANSFORMERS_CACHE"] = "D:/hf_cache/transformers"
client = genai.Client()
# Download punkt for sentence tokenization
# nltk.download('punkt', quiet=True)
# _sent_tokenize = nltk.sent_tokenize
# Load distilled Pegasus (smaller than pegasus-arxiv)
def _sent_tokenize(text: str):
    import re
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9(])', text.strip())
    return [s for s in sents if s]

pegasus_summarizer = pipeline(
    "summarization",
    model="google/pegasus-arxiv",   # or "sshleifer/distill-pegasus-xsum"
    tokenizer="google/pegasus-arxiv",
    device=0
)

def clean_summary(text: str) -> str:
    # remove Pegasus artifacts
    text = text.replace("<n>", " ")
    text = re.sub(r"\s{2,}", " ", text)  # collapse multiple spaces
    return text.strip()

def _chunk_sentences(text: str, max_chars: int = 2200, overlap_sents: int = 1):
    """Split text into sentence chunks with slight overlap for context."""
    sents = _sent_tokenize(text)
    chunks, cur, cur_len = [], [], 0
    for s in sents:
        if cur_len + len(s) > max_chars and cur:
            chunks.append(" ".join(cur))
            cur = cur[-overlap_sents:] if overlap_sents else []
            cur_len = sum(len(x) for x in cur)
        cur.append(s)
        cur_len += len(s)
    if cur:
        chunks.append(" ".join(cur))
    return chunks

def summarize_with_pegasus(text: str, bullets: int = 4) -> str:
    """Summarize academic text into concise bullet points using distilled Pegasus."""
    text = text.strip()
    if not text or len(text) < 50:
        return "Text too short for summarization."

    # Chunk input for long abstracts
    chunks = _chunk_sentences(text)

    # First pass summaries
    partial_summaries = []
    for chunk in chunks:
        out = pegasus_summarizer(
            chunk,
            truncation=True,
            max_length=180,
            min_length=70,
            do_sample=False,
            num_beams=4
        )[0]["summary_text"]
        partial_summaries.append(out)

    # Second pass to fuse summaries
    fused_input = " ".join(partial_summaries)
    fused_summary = pegasus_summarizer(
        fused_input,
        truncation=True,
        max_length=220,
        min_length=80,
        do_sample=False,
        num_beams=4
    )[0]["summary_text"]
    fused_summary = clean_summary(fused_summary)
    # Convert to bullet points
    sents = [s.strip() for s in re.split(r"[.;]\s+", fused_summary) if s.strip()]
    sents = sents[:bullets]
    return "\n".join(f"* {s}" for s in sents)


extractive_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
def clean_bullets(text: str) -> str:
    points = [pt.strip(" .\n") for pt in text.split("•") if pt.strip()]
    return "\n".join([f"* {pt}" for pt in points])

def chunk_text(text: str, chunk_size: int = 1500) -> list:
    # Split into roughly word-length chunks (~500-600 words per chunk)
    return textwrap.wrap(text, chunk_size)

def format_as_bullets(paragraphs: list) -> str:
    return "\n".join([f"• {sent.strip().rstrip('.')}" for sent in paragraphs if sent.strip()])

def summarize_with_bart(text: str) -> str:
    try:
        if not extractive_summarizer:
            return "Extractive summarizer not available."

        if not text or len(text.strip()) < 50:
            return "Text too short for summarization."

        chunks = chunk_text(text)
        all_summaries = []

        for chunk in chunks:
            summary = extractive_summarizer(
                chunk,
                 
                max_length=300, 
                min_length=60, 
                do_sample=False, 
               )
            summarized_text = summary[0]['summary_text']
            all_summaries.append(summarized_text)
        bullets = format_as_bullets(all_summaries).split("\n")
        bullets = [b for b in bullets if b.strip()][:4]  # keep only first 4
        return clean_bullets("\n".join(bullets))

        #return clean_bullets(format_as_bullets(all_summaries))


    except Exception as e:
        logging.error(f"[BART Summarizer Error] {e}")
        return "Extractive summarization failed."
    
def summarize_with_gemini(text: str) -> str:
    prompt = f"""Assume you are an expert researcher. Now summarize the following academic abstract in 3-4 bullet points.
      Make each point as concise as possible:
    
{text}

"""
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",  
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config=types.GenerateContentConfig(
                temperature=0.3,
                top_k=40,
                top_p=0.95,
            )
        )
        return response.text.strip()
    except Exception as e:
        print("[Gemini Keyword Error]", e)
        return "Gemini summarization failed."
