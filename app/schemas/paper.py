from pydantic import BaseModel
from typing import List, Optional

class PaperBase(BaseModel):
    title:str
    abstract:str
    summary: Optional[str]=None
    keywords: Optional[List[str]] = []
    chat: Optional[List[dict]] = []
    favorite: Optional[bool] = False 