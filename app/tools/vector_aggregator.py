# app/tools/vector_aggregator.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.connect_db.mongo_client import products
from bson import ObjectId
import os

model = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))


class VectorInput(BaseModel):
    product_ids: List[str] = Field(..., description="List product IDs")


class VectorAggregatorTool(BaseTool):
    name: str = "compute_user_vector"
    description: str = "Tính vector trung bình từ danh sách sách"
    args_schema: Type[BaseModel] = VectorInput

    def _run(self, product_ids: List[str]) -> List[float]:
        embeddings = []
        for pid in set(product_ids):
            try:
                doc = products.find_one({"_id": ObjectId(pid)})
                if doc:
                    text = f"{doc.get('name','')}. {doc.get('category',{}).get('name','')}. {doc.get('description','')}"
                    if text.strip():
                        emb = model.encode(text.strip(), normalize_embeddings=True)
                        embeddings.append(emb)
            except:
                continue
        return np.mean(embeddings, axis=0).tolist() if embeddings else [0.0] * 768
