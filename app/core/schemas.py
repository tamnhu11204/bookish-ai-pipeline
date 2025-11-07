# ai_service/app/core/schemas.py
from pydantic import BaseModel
from typing import List, Optional


# Schema cho API tìm kiếm
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


# Schema cho API gợi ý
class RecommendRequest(BaseModel):
    user_id: str


# Có thể thêm các schema cho response nếu muốn định nghĩa chặt chẽ hơn
class ProductInfo(BaseModel):
    id: str
    name: Optional[str]
    author: Optional[str]
    category: Optional[str]
    img: Optional[str]


class RecommendationItem(BaseModel):
    chunk_id: str
    product_id: Optional[str]
    score: Optional[float]
    product: Optional[ProductInfo]


class RecommendationGroup(BaseModel):
    title: str
    books: List[RecommendationItem]


class BehaviorRecommendationResponse(BaseModel):
    user_id: str
    note: str
    recommended: List[RecommendationItem]
    groups: List[RecommendationGroup]


class ComboItem(BaseModel):
    title: str
    reason: str
    book_ids: List[str]


class ComboResponse(BaseModel):
    combos: List[ComboItem]
