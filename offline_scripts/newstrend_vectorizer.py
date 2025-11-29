# app/api/news_vectorizer.py
import sys
import os
# THÊM 3 DÒNG NÀY – CHỐNG LỖI 100%
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.connect_db.vector_db import news_vectors, get_model

router = APIRouter(prefix="/ai/news")
model = get_model()


class ArticleInput(BaseModel):
    id: str
    title: str
    content: str


class VectorizeRequest(BaseModel):
    articles: List[ArticleInput]


def vectorize_articles(articles: List[ArticleInput]):
    if not articles:
        return
    texts = [f"{a.title}. {a.content}" for a in articles]
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()
    now = int(datetime.utcnow().timestamp())

    news_vectors.add(
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"source_id": a.id, "type": "news", "title": a.title, "timestamp": now}
            for a in articles
        ],
        ids=[a.id for a in articles],
    )
    print(f"[VECTORIZED] {len(articles)} tin tức")


@router.post("/vectorize")
async def vectorize_news(req: VectorizeRequest, background: BackgroundTasks):
    background.add_task(vectorize_articles, req.articles)
    return {"status": "ok", "count": len(req.articles)}
