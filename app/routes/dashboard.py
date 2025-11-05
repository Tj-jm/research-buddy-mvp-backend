from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from app.db import get_db
from app.services.b2 import upload_file, download_file, delete_file
from app.core.auth import get_current_user
from app.schemas.paper import PaperBase
from bson import ObjectId
import tempfile, os
from bson import objectid
from fastapi import Query
from typing import Optional
from datetime import datetime

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# ----------------------
# 1. POST - Create Paper
# ----------------------
@router.post("/papers")
async def create_paper(
    title: str = Form(...),
    abstract: str = Form(...),
    summary: str = Form(None),
    keywords: str = Form(None),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Upload to B2
    key = f"papers/{user}/{file.filename}"
    file_url = upload_file(os.getenv("B2_BUCKET"), key, tmp_path)
    os.remove(tmp_path)

    # Document for Mongo
    paper_doc = {
        "owner": user,
        "title": title,
        "abstract": abstract,
        "summary": summary,
        "keywords": keywords.split(",") if keywords else [],
        "file_url": file_url,
        "file_key":key,
        "original_filename": file.filename,
        "chat": [],
        "created_at": datetime.utcnow(),
        "favorite": False, 
    }

    result = await db.papers.insert_one(paper_doc)
    return {"inserted_id": str(result.inserted_id), "file_url": file_url}

# ----------------------
# 2. GET - All Papers
# ----------------------
@router.get("/papers")
async def get_papers(
    user=Depends(get_current_user),
    db=Depends(get_db),
    # Pagination
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    # Sorting
    sort_by: str = Query("title", description="Field to sort by (title, created_at, etc.)"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    # Search / filter
    search: Optional[str] = Query(None, description="Search in title, abstract, or keywords"),
    favorite_only: bool = Query(False, description="Return only favorite papers")
    ):
    query = {"owner": user}

    # Search filter
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"abstract": {"$regex": search, "$options": "i"}},
            {"keywords": {"$regex": search, "$options": "i"}},
        ]
    if favorite_only:
        query["favorite"] = True
    # Sorting
    sort_dir = 1 if sort_order == "asc" else -1

    # Pagination calculation
    skip = (page - 1) * limit

    cursor = (
        db.papers.find(query)
        .sort(sort_by, sort_dir)
        .skip(skip)
        .limit(limit)
    )
    papers = [serialize_doc(doc) async for doc in cursor]

    # Total count (for frontend pagination)
    total = await db.papers.count_documents(query)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "results": papers
    }

# ----------------------
# 3. GET - Single Paper
# ----------------------
@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    paper = await db.papers.find_one({"_id": ObjectId(paper_id), "owner": user})
    if not paper:
        raise HTTPException(404, "Paper not found")
    return serialize_doc(paper)

# ----------------------
# 4. PUT - Update Paper
# ----------------------
@router.put("/papers/{paper_id}")
async def update_paper(paper_id: str, data: PaperBase, user=Depends(get_current_user), db=Depends(get_db)):
    result = await db.papers.update_one(
        {"_id": ObjectId(paper_id), "owner": user},
        {"$set": data.dict(exclude_unset=True)}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Paper not found or unauthorized")
    return {"msg": "Paper updated"}

# ----------------------
# 5. DELETE - Paper (DB + B2)
# ----------------------
@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    paper = await db.papers.find_one({"_id": ObjectId(paper_id), "owner": user})
    if not paper:
        raise HTTPException(404, "Paper not found or unauthorized")

    # Delete file from B2 using stored file_key
    file_key = paper.get("file_key")
    bucket = os.getenv("B2_BUCKET")
    if file_key:
        try:
            delete_file(bucket, file_key)
        except Exception as e:
            print(f"Error deleting from B2: {e}")


    # Delete doc from Mongo
    await db.papers.delete_one({"_id": ObjectId(paper_id), "owner": user})
    return {"msg": "Paper deleted"}


# ----------------------
# 6. GET - Download Paper
# ----------------------

@router.get("/papers/{paper_id}/download")
async def download_paper(paper_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    paper = await db.papers.find_one({"_id": ObjectId(paper_id), "owner": user})
    if not paper:
        raise HTTPException(404, "Paper not found")

    bucket = os.getenv("B2_BUCKET")
    file_key = paper["file_key"]   

    tmp_path = os.path.join(tempfile.gettempdir(), f"{paper_id}.pdf")
    download_file(bucket, file_key, tmp_path)

    download_name = paper.get("original_filename") or f"{paper['title']}.pdf"

    response = FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename=download_name
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response
# ----------------------------
# 7. PUT - Make Favorite Paper
# ----------------------------
@router.put("/papers/{paper_id}/favorite")
async def toggle_favorite(
    paper_id: str,
    favorite: bool,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    result = await db.papers.update_one(
        {"_id": ObjectId(paper_id), "owner": user},
        {"$set": {"favorite": favorite}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Paper not found or unauthorized")
    return {"msg": f"Paper marked as {'favorite' if favorite else 'not favorite'}"}


# @router.get("/papers/{paper_id}/download")
# async def download_paper(paper_id: str, user=Depends(get_current_user), db=Depends(get_db)):
#     paper = await db.papers.find_one({"_id": ObjectId(paper_id), "owner": user})
#     if not paper:
#         raise HTTPException(404, "Paper not found")

#     key = "/".join(paper["file_url"].split("/")[-3:])
#     bucket = os.getenv("B2_BUCKET")

#      # Create a safe temp file path (not opened/locked)
#     tmp_path = os.path.join(tempfile.gettempdir(), f"{paper_id}.pdf")

    # Download file to path
    # download_file(bucket, key, tmp_path)

    # Return file response
    # return FileResponse(tmp_path, media_type="application/pdf", filename=paper["title"] + ".pdf")

    # with tempfile.NamedTemporaryFile(delete=False) as tmp:
    #     download_file(bucket, key, tmp.name)
    #     tmp_path = tmp.name

    #return FileResponse(tmp_path, filename=key.split("/")[-1], media_type="application/pdf")
