# app/tools/semantic_retriever.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type, List
from app.connect_db.vector_db import recommend_vectors


class RetrieverInput(BaseModel):
    user_vector: List[float] = Field(..., description="Vector người dùng")
    top_k: int = Field(20, ge=1, le=100)
    exclude_ids: Optional[List[str]] = Field(default_factory=list)
    category_boost: Optional[List[str]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class SemanticRetrieverTool(BaseTool):
    name: str = "search_similar_books"
    description: str = "Tìm sách tương đồng từ ChromaDB"
    args_schema: Type[BaseModel] = RetrieverInput

    def _run(
        self,
        user_vector: List[float],
        top_k: int = 20,
        exclude_ids: List[str] = None,
        category_boost: List[str] = None,
    ) -> List[str]:
        exclude_ids = exclude_ids or []
        category_boost = category_boost or []

        # === XÂY DỰNG WHERE CLAUSE AN TOÀN ===
        where_clauses = []

        # 1. Loại bỏ sách đã mua/xem
        if exclude_ids:
            where_clauses.append({"source_id": {"$nin": exclude_ids}})

        # 2. Ưu tiên thể loại
        if category_boost:
            where_clauses.append({"category": {"$in": category_boost}})

        # Ghép điều kiện bằng $and
        where = {"$and": where_clauses} if where_clauses else None

        # === QUERY ===
        try:
            res = recommend_vectors.query(
                query_embeddings=[user_vector],
                n_results=top_k + len(exclude_ids),  # bù thêm
                where=where,  # ← chỉ truyền nếu không None
                include=["metadatas", "distances"],
            )

            results = []
            seen = set()
            for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
                sid = meta.get("source_id")
                if sid and sid not in exclude_ids and sid not in seen:
                    results.append(sid)
                    seen.add(sid)
                    if len(results) >= top_k:
                        break
            return results

        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return []
