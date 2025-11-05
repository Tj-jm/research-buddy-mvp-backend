from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from app.schemas.faculty_scrape import FacultyScrapeIn, FacultyScrapeOut
from datetime import datetime
import os, time

from app.agents.faculty_scrapper.scraper import AdaptiveFacultyScraper
from app.agents.faculty_scrapper.deep_screaper import EnhancedFacultyScraper
from app.utils.progress import get_progress, clear_progress

router = APIRouter(prefix="/faculty", tags=["Agent"])


def _pick_engine(mode: str, use_selenium: bool, deep: bool, max_visits=None):
    if mode == "deep_scrape":
        return EnhancedFacultyScraper(
            use_selenium=use_selenium,
            deep_scrape=deep,
            max_profile_visits=max_visits,
        )
    return AdaptiveFacultyScraper(
        use_selenium=use_selenium,
        deep_scrape=deep,
        max_profile_visits=max_visits,
    )


@router.post("/scrape", response_model=FacultyScrapeOut)
def scrape_faculty(payload: FacultyScrapeIn):
    try:
        engine = _pick_engine(
            mode=payload.mode,
            use_selenium=payload.use_selenium,
            deep=(payload.mode == "deep_scrape"),
            max_visits=payload.max_profile_visits,
        )

        results = engine.scrape_faculty(payload.url)

        if not results:
            raise HTTPException(status_code=422, detail="No faculty data found for this URL.")

        # generate filename with timestamp
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"faculty_{ts}.xlsx"

        # save Excel file
        engine.save_to_excel(results, filename)

        stats = {
            "total": len(results),
            "with_email": sum(1 for r in results if r.get("email")),
            "with_research": sum(1 for r in results if r.get("research_interests")),
            "with_profile_url": sum(1 for r in results if r.get("profile_url")),
        }

        return {
            "rows": results,
            "stats": stats,
            "files": {
                "xlsx": {
                    "filename": filename,
                    "url": f"/faculty/download/{filename}",
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {e}")


@router.get("/download/{filename}")
def download_file(filename: str):
    folder = os.path.join(os.getcwd(), "faculty_documents_deep")
    filepath = os.path.join(folder, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/progress")
def scrape_progress(task_id: str = "scrape"):
    def event_stream():
        while True:
            percent = get_progress(task_id)
            yield f"data: {percent}\n\n"
            if percent >= 100:
                break
            time.sleep(1)
    return StreamingResponse(event_stream(), media_type="text/event-stream")