# app/tools/semantic_retriever.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List
from app.connect_db.vector_db import product_vectors


class RetrieverInput(BaseModel):
    user_vector: List[float]
    top_k: int = Field(10)


class SemanticRetrieverTool(BaseTool):
    name: str = "search_similar_books"
    description: str = "Tìm sách tương đồng từ ChromaDB"
    args_schema: Type[BaseModel] = RetrieverInput

    def _run(self, user_vector: List[float], top_k: int = 10) -> List[str]:
        try:
            res = product_vectors.query(
                query_embeddings=[user_vector], n_results=top_k, include=["metadatas"]
            )
            return [m["source_id"] for m in res["metadatas"][0] if m.get("source_id")]
        except:
            return []
