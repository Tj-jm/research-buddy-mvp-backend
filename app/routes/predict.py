from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from PyPDF2 import PdfReader
from app.schemas.predict import (
    PredictRequest,
    PredictResponse,
    AllModelsResponse,
    SingleModelPrediction,
    UnifiedResponse,
    KeywordRequest,
    KeywordResponse,
    KeywordTextRequest,
    SummaryRequest,
    SummaryResponse
)
from typing import Union
from fastapi.responses import JSONResponse
from app.services.loader import load_all_models
from app.services.predictor import predict_label
from app.services.keyword_extractor import (extract_keywords_keybert,extract_keywords_gemini)
from app.services.summarizer import summarize_with_gemini, summarize_with_bart,summarize_with_pegasus

router =APIRouter()

models,tokenizers, label_encoder,tfidf_vectorizer = load_all_models()

@router.post("/predict", response_model=Union[PredictResponse, AllModelsResponse])
def predict(request: PredictRequest):
    if request.model_name != "ALL" and request.model_name not in models:
        raise HTTPException(status_code=400, detail="Model Not Found")

    try:
        output, confidence = predict_label(
            request.abstract, request.model_name, models, tokenizers, label_encoder
        )

        # Single model
        if request.model_name != "ALL":
            return PredictResponse(predicted_label=output, confidence=confidence)

        # ALL models — return raw dict
        return {"predictions": output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-pdf", response_model=UnifiedResponse)
async def predict_from_pdf( pdf_file: UploadFile = File(...),model_name:str = Form(...) ):
    # Validate model
    if model_name != "ALL" and model_name not in models:
        raise HTTPException(status_code=400, detail="Model Not Found")

    try:
        contents = await pdf_file.read()
        pdf = PdfReader(pdf_file.file)
        abstract=""
        
        for page in pdf.pages[:2]:  # First 2 pages typically include abstract
            abstract += page.extract_text() or ""

        if not abstract.strip():
            raise HTTPException(status_code=400, detail="No text extracted from PDF.")

        # Predict
        result = predict_label(abstract, model_name, models, tokenizers, label_encoder)

        if model_name == "ALL":
            predictions, _ = result
            return UnifiedResponse(
                abstract=abstract.strip(),
                result=AllModelsResponse(predictions=predictions)
            )
        else:
            label, confidence = result
            return UnifiedResponse(
                abstract=abstract.strip(),
                result=PredictResponse(predicted_label=label, confidence=confidence)
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract_keywords_pdf", response_model=KeywordResponse)
async def extract_keywords_from_pdf(
    pdf_file: UploadFile = File(...),
    top_n: int = Form(10)
):
    try:
        pdf = PdfReader(pdf_file.file)
        text = ""
        for page in pdf.pages[:2]:  # Assume abstract is early
            text += page.extract_text() or ""

        if not text.strip():
            raise HTTPException(status_code=400, detail="No text extracted from PDF.")

        keywords = extract_keywords_keybert(text,  top_n)
        return {"keywords": keywords}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract_keywords_text", response_model=KeywordResponse)
async def extract_keywords_from_text(payload: KeywordTextRequest):
    """
    Extract keywords from raw abstract text using KeyBERT
    """
    try:
        if not payload.abstract.strip():
            raise HTTPException(status_code=400, detail="Empty abstract received.")

        keywords = extract_keywords_keybert(payload.abstract, top_n=payload.top_n)
        return {"keywords": keywords}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/extract_keywords_gemini", response_model=KeywordResponse)
async def extract_keywords_with_gemini(payload: KeywordTextRequest):
    try:
        if not payload.abstract.strip():
            raise HTTPException(status_code=400, detail="Empty abstract received.")
        keywords = extract_keywords_gemini(payload.abstract, top_n=payload.top_n)
        return {"keywords": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/summarize", response_model=SummaryResponse)
def summarize(request: SummaryRequest):
    try:
        if request.model_name == "gemini":
            summary = summarize_with_gemini(request.abstract)
        elif request.model_name == "bart":
            summary = summarize_with_bart(request.abstract)
        else:
            raise HTTPException(status_code=400, detail="Unsupported model.")
        
        return {"summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))