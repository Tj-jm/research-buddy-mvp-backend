from pydantic import BaseModel
from typing import List, Dict, Optional

class FacultyScrapeDBIn(BaseModel):
    url: str                         
    rows: List[Dict]
    stats: Dict
    files: Dict                      
    filetype: Optional[str] = None   

class FacultyScrapeDB(FacultyScrapeDBIn):
    id: str
