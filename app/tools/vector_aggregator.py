# app/tools/vector_aggregator.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List
import numpy as np
from app.connect_db.vector_db import recommend_vectors


class VectorInput(BaseModel):
    product_ids: List[str]


class VectorAggregatorTool(BaseTool):
    name: str = "compute_user_vector"
    description: str = "Tính vector trung bình từ danh sách sách (dùng vector đã lưu)"
    args_schema: Type[BaseModel] = VectorInput

    def _run(self, product_ids: List[str]) -> List[float]:
        embeddings = []
        for pid in set(product_ids):
            try:
                result = recommend_vectors.get(
                    where={"source_id": pid}, include=["embeddings"]
                )
                if result["embeddings"]:
                    embeddings.append(result["embeddings"][0])
            except:
                continue
        return np.mean(embeddings, axis=0).tolist() if embeddings else [0.0] * 768
