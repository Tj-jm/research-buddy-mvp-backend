from fastapi import APIRouter, HTTPException, Query
from app.schemas.faculty_scrape_db import FacultyScrapeDB, FacultyScrapeDBIn
from app.db import db
from bson import ObjectId

router = APIRouter(prefix="/faculty-scrape-db", tags=["FacultyScrapeDB"])

collection = db["faculty_scrapes"]

@router.post("/save", response_model=FacultyScrapeDB)
async def save_scrape(payload: FacultyScrapeDBIn):
    try:
        doc = payload.dict()
        res = await collection.insert_one(doc)
        return FacultyScrapeDB(id=str(res.inserted_id), **doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")



@router.get("/list")
async def list_scrapes(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100)
):
    skip = (page - 1) * limit
    total = await collection.count_documents({})
    items = await collection.find().skip(skip).limit(limit).to_list(limit)

    return {
        "items": [
            FacultyScrapeDB(
                id=str(item["_id"]),
                url=item.get("url", ""),
                rows=item.get("rows", []),
                stats=item.get("stats", {}),
                files=item.get("files", {}),
                filetype=item.get("filetype")
            )
            for item in items
        ],
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit,
    }




@router.get("/{scrape_id}", response_model=FacultyScrapeDB)
async def get_scrape(scrape_id: str):
    try:
        oid = ObjectId(scrape_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    doc = await collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Scrape not found")

    return FacultyScrapeDB(
        id=str(doc["_id"]),
        url=doc.get("url", ""),
        rows=doc.get("rows", []),
        stats=doc.get("stats", {}),
        files=doc.get("files", {}),
        filetype=doc.get("filetype")
    )

@router.delete("/{scrape_id}")
async def delete_scrape(scrape_id: str):
    try:
        oid = ObjectId(scrape_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    result = await collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scrape not found")

    return {"status": "success", "deleted_id": scrape_id}