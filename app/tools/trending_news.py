# app/tools/trending_news.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Type
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import MiniBatchKMeans
import os

from app.connect_db.vector_db import news_vectors

model = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))


# ← SCHEMA INPUT
class TrendingInput(BaseModel):
    top_k: int = Field(5, ge=1, le=10)


# ← SỬA: THÊM TYPE ANNOTATION CHO args_schema
class TrendingNewsTool(BaseTool):
    name: str = "get_trending_topics"
    description: str = "Lấy top K chủ đề hot từ tin tức 24h gần nhất"
    args_schema: Type[BaseModel] = TrendingInput

    def _run(self, top_k: int = 5) -> List[Dict]:
        try:
            results = news_vectors.query(
                query_texts=["tin tức"],
                n_results=100,
                include=["documents", "metadatas"],
            )

            texts = results["documents"][0]
            if not texts:
                return []

            embs = model.encode(texts, normalize_embeddings=True)
            k = min(top_k, len(embs))
            if k == 1:
                labels = np.zeros(len(embs), dtype=int)
            else:
                km = MiniBatchKMeans(n_clusters=k, batch_size=128, random_state=42)
                labels = km.fit_predict(embs)

            topics = []
            for i in range(k):
                mask = labels == i
                cluster_texts = [texts[j] for j in range(len(texts)) if mask[j]]
                if cluster_texts:
                    rep = max(cluster_texts, key=len)[:140]
                    score = mask.sum() / len(embs)
                    topics.append(
                        {
                            "topic": rep.strip(),
                            "score": round(float(score), 3),
                            "articles": int(mask.sum()),
                        }
                    )

            return sorted(topics, key=lambda x: x["score"], reverse=True)[:top_k]

        except Exception as e:
            print(f"[ERROR] TrendingNewsTool: {e}")
            return []
