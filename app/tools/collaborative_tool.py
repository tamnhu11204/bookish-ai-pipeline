# app/tools/collaborative_tool.py
import os
import json
from typing import List, Dict, Optional
from langchain_core.tools import BaseTool
from heapq import nlargest


class CollaborativeFilteringTool(BaseTool):
    name: str = "collab_filter"
    description: str = (
        "Gợi ý sách dựa trên hành vi cộng đồng. "
        'Input: {"product_ids": List[str], "top_k": int (optional, default 20)}'
    )

    _similarity: Dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load()

    def _load(self):
        path = "./offline_scripts/data/item_similarity.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._similarity = json.load(f)
            print(f"[CF Tool] Đã tải {len(self._similarity)} sách từ {path}")
        else:
            print(
                f"[CF Tool] Không tìm thấy {path} → Chạy script compute_item_similarity.py"
            )

    # SỬA: Thay đổi chữ ký (signature) của hàm _run
    def _run(self, product_ids: List[str], top_k: int = 20) -> List[Dict]:
        """
        Hàm _run bây giờ nhận trực tiếp `product_ids` và `top_k`.
        Điều này khớp với cách LangChain gọi tool.
        """
        if not product_ids or not self._similarity:
            return []

        scores = {}
        for pid in product_ids:
            if pid in self._similarity:
                for sid, score in self._similarity[pid].items():
                    # Tăng điểm cho các sách tương tự
                    scores[sid] = scores.get(sid, 0) + score

        # Loại bỏ những sách người dùng đã tương tác ra khỏi danh sách ứng viên
        candidates = {k: v for k, v in scores.items() if k not in product_ids}

        # Lấy ra top_k sách có điểm cao nhất
        top = nlargest(top_k, candidates.items(), key=lambda x: x[1])

        return [{"book_id": k, "score": round(v, 4)} for k, v in top]

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not supported")
