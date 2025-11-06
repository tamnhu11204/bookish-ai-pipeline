from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.search_service import hybrid_search

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


@router.post("/search")
async def search_books(req: SearchRequest):
    """
    API tìm kiếm sách dựa trên ngữ nghĩa (semantic search).
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="Thiếu tham số query")

    try:
        results = hybrid_search(query=req.query, top_k=req.top_k)
        return {"product_ids": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tìm kiếm: {e}")
