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

        # 1. Loại bỏ sách đã mua/xem (Sử dụng $nin)
        if exclude_ids:
            # Lọc bỏ các ID không hợp lệ nếu có
            clean_exclude = [str(i) for i in exclude_ids if i]
            if clean_exclude:
                where_clauses.append({"source_id": {"$nin": clean_exclude}})

        # 2. Ưu tiên thể loại (Sử dụng $in)
        if category_boost:
            # Lọc bỏ giá trị "Không rõ" để tránh query nhiễu
            clean_cats = [c for c in category_boost if c and c != "Không rõ"]
            if clean_cats:
                where_clauses.append({"category": {"$in": clean_cats}})

        # === FIX LỖI $and PHẢI CÓ ÍT NHẤT 2 PHẦN TỬ ===
        where = None
        if len(where_clauses) > 1:
            where = {"$and": where_clauses}
        elif len(where_clauses) == 1:
            where = where_clauses[0]  # Truyền trực tiếp điều kiện duy nhất

        # === QUERY ===
        try:
            # n_results nên lấy dư ra một chút để trừ hao sau khi lọc trùng
            fetch_count = top_k + len(exclude_ids)
            if fetch_count > 100:
                fetch_count = 100  # Giới hạn của Chroma thường là 100

            res = recommend_vectors.query(
                query_embeddings=[user_vector],
                n_results=fetch_count,
                where=where,
                include=["metadatas", "distances"],
            )

            if not res or not res.get("metadatas") or len(res["metadatas"]) == 0:
                return []

            results = []
            seen = set()
            # Lọc lại một lần nữa ở code để đảm bảo an toàn tuyệt đối
            for meta in res["metadatas"][0]:
                sid = meta.get("source_id")
                if sid and sid not in exclude_ids and sid not in seen:
                    results.append(sid)
                    seen.add(sid)
                    if len(results) >= top_k:
                        break
            return results

        except Exception as e:
            # Log lỗi chi tiết để debug nhưng không làm sập hệ thống
            print(f"[ERROR] SemanticRetrieverTool Query failed: {e}")
            # Trong trường hợp lỗi query (ví dụ metadata không tồn tại),
            # trả về list rỗng để chain có thể dùng fallback
            return []
