from typing import Optional, Dict, Union
from pydantic import BaseModel
from typing import Literal
class SingleModelPrediction(BaseModel):
    label: str
    confidence: Optional[float]

class PredictRequest(BaseModel):
    model_name: str
    abstract: str

class PredictResponse(BaseModel):
    predicted_label: str
    confidence: Optional[float]

class AllModelsResponse(BaseModel):
    predictions: Dict[str, SingleModelPrediction]
class UnifiedResponse(BaseModel):
    abstract: str
    result: Union[PredictResponse, AllModelsResponse]

class KeywordRequest(BaseModel):
    text: str
    top_n: int = 10

class KeywordResponse(BaseModel):
    keywords: list[str]

class KeywordTextRequest(BaseModel):
    abstract: str
    top_n: Optional[int] = 5

class SummaryRequest(BaseModel):
    abstract: str
    model_name: Literal["gemini", "bart"]

class SummaryResponse(BaseModel):
    summary: str

