# app/schemas/faculty_scrape.py
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict

class FacultyScrapeIn(BaseModel):
    url: str
    mode: Literal["scrape", "deep_scrape"] = "scrape"
    use_selenium: bool = True
    max_profile_visits: Optional[int] = None
    filetype: Literal["csv", "xlsx", "both"] = "both"

class FacultyScrapeOut(BaseModel):
    rows: List[Dict]
    stats: Dict
    files: Dict
