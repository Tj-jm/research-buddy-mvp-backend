from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.agents.faculty_scrapper.schema import ScrapeRequest, ScrapeResponse, FacultyProfile
from app.agents.faculty_scrapper.graph import run_scraper
import base64
import traceback

router = APIRouter()

@router.post("/faculty-scraper", response_model=ScrapeResponse)
async def faculty_scraper(req: ScrapeRequest):
    try:
        result = await run_scraper(
            directory_url=str(req.directory_url),
            provider=req.provider,
            max_profiles=req.max_profiles
        )

        rows = result["normalized"]

        # Clean rows: drop unknown keys
        clean_rows = []
        for r in rows:
            try:
                clean_rows.append(FacultyProfile(**r).model_dump())
            except Exception:
                # skip invalid row or pop extra fields
                valid = {k: v for k, v in r.items() if k in FacultyProfile.model_fields}
                clean_rows.append(valid)

        # Ensure csv_base64 is str
        csv_b64 = result["csv_base64"]
        if isinstance(csv_b64, (bytes, bytearray)):
            csv_b64 = base64.b64encode(csv_b64).decode("utf-8")

        resp = ScrapeResponse(
            data=clean_rows,
            csv_filename=result.get("csv_filename", "faculty.csv"),
            csv_base64=csv_b64,
        )
        return JSONResponse(resp.model_dump())

    except Exception as e:
        import logging
        logging.getLogger("scraper").error("faculty-scraper failed:\n" + traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Scraper crashed: {e}")
