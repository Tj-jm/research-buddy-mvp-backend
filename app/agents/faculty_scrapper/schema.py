from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional

class FacultyProfile(BaseModel):
    professor_name: str = Field(..., alias="Professor Name")
    designation: Optional[str] = Field(None, alias="Designation")
    university_name: Optional[str] = Field(None, alias="University Name")
    email: Optional[EmailStr] = Field(None, alias="Email")
    profile_link: Optional[HttpUrl] = Field(None, alias="Profile Link")
    hook_point: Optional[str] = Field(None, alias="Hook Point")
    research_interests: Optional[str] = Field(None, alias="Research Interests")
    personal_website: Optional[str] = Field(None, alias="Personal Website")
    google_scholar: Optional[str] = Field(None, alias="Google Scholar")
    bio: Optional[str] = Field(None, alias="Bio")
    source: str = Field("Website Search", alias="Source")
    subject: Optional[str] = Field(None, alias="Subject")  # AI/ML | Education & Leadership | Data Science

    class Config:
        populate_by_name = True

class ScrapeRequest(BaseModel):
    directory_url: HttpUrl
    max_profiles: int | None = None
    use_js: bool | None = None
    provider: Optional[str] = None  # override env (gemini|local)

class ScrapeResponse(BaseModel):
    data: List[FacultyProfile]
    csv_filename: str
    csv_base64: str  # downloadable in frontend
