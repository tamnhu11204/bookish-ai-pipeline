# app/tools/vector_aggregator.py – PHIÊN BẢN VĨNH VIỄN KHÔNG TREO, CHẠY ĐƯỢC TRÊN TẤT CẢ CHROMA
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Type
import numpy as np
from app.connect_db.vector_db import recommend_vectors


class VectorInput(BaseModel):
    product_ids: List[str] = Field(..., description="Danh sách ID sách đã tương tác")


class VectorAggregatorTool(BaseTool):
    name: str = "compute_user_vector"
    description: str = (
        "Tính vector trung bình – siêu nhanh, không treo, tương thích mọi Chroma"
    )
    args_schema: Type[BaseModel] = VectorInput

    def _run(self, product_ids: List[str]) -> List[float]:
        if not product_ids:
            return [0.0] * 768

        unique_ids = list(set(product_ids))
        if not unique_ids:
            return [0.0] * 768

        try:
            # DÙNG .query() + DUMMY VECTOR + where $in → NHANH + KHÔNG TREO
            result = recommend_vectors.query(
                query_embeddings=[[0.0] * 768],  # dummy vector
                where={"source_id": {"$in": unique_ids}},
                n_results=len(unique_ids),
                include=["embeddings"],
            )

            embeddings = result.get("embeddings", [])
            if not embeddings or len(embeddings) == 0 or len(embeddings[0]) == 0:
                print(
                    "[VectorAggregator] Không tìm thấy embedding → trả về zero vector"
                )
                return [0.0] * 768

            # embeddings[0] là list các vector → chuyển thành np.array
            emb_array = np.array(embeddings[0], dtype=np.float32)
            if emb_array.size == 0:
                return [0.0] * 768

            avg_vec = np.mean(emb_array, axis=0)
            norm = np.linalg.norm(avg_vec)

            if norm < 1e-8:
                return [0.0] * 768

            return (avg_vec / norm).tolist()

        except Exception as e:
            print(f"[VectorAggregator] Lỗi → trả về zero vector: {e}")
            return [0.0] * 768
