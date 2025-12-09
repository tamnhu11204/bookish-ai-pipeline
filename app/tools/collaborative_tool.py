# app/tools/collaborative_tool.py 

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import os
from heapq import nlargest


class CollabInput(BaseModel):
    product_ids: List[str] = Field(
        ..., description="Danh sách ID sản phẩm người dùng đã tương tác"
    )
    top_k: int = Field(20, ge=1, le=200, description="Số lượng sách gợi ý")


class CollaborativeFilteringTool(StructuredTool):
    name: str = "collab_filter"
    description: str = (
        "Gợi ý sách dựa trên hành vi cộng đồng (item-to-item collaborative filtering offline)"
    )

    # QUAN TRỌNG NHẤT: DÙNG TYPE ANNOTATION CHO args_schema
    args_schema: type[BaseModel] = (
        CollabInput  # ← Đây là cách đúng duy nhất với Pydantic v2
    )

    _similarity: Dict[str, Dict[str, float]] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_similarity()

    def _load_similarity(self):
        path = "./offline_scripts/data/item_similarity.json"
        if not os.path.exists(path):
            print(
                f"[CF Tool] Không tìm thấy {path} → chạy script compute_item_similarity.py"
            )
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._similarity = {
                    str(k): {str(k2): float(v2) for k2, v2 in v.items()}
                    for k, v in data.items()
                }
            print(
                f"[CF Tool] Đã tải {len(self._similarity)} sách từ item_similarity.json"
            )
        except Exception as e:
            print(f"[CF Tool] Lỗi load similarity: {e}")

    def _run(self, product_ids: List[str], top_k: int = 20) -> List[Dict[str, Any]]:
        if not product_ids or not self._similarity:
            return []

        scores: Dict[str, float] = {}
        interacted_set = set(product_ids)

        for pid in product_ids:
            if pid in self._similarity:
                for similar_id, score in self._similarity[pid].items():
                    if similar_id not in interacted_set:
                        scores[similar_id] = scores.get(similar_id, 0.0) + score

        if not scores:
            return []

        top_items = nlargest(top_k, scores.items(), key=lambda x: x[1])
        return [
            {"book_id": book_id, "score": round(score, 4)}
            for book_id, score in top_items
        ]
