# app/tools/user_similarity_tool.py
import json
import os
from typing import List
from langchain_core.tools import BaseTool
from pydantic import Field  # ← quan trọng

PATH = "./offline_scripts/data/user_similarity.json"

class UserSimilarityTool(BaseTool):
    name: str = "find_similar_users"
    description: str = "Trả về danh sách user_id (str) có hành vi giống nhất với user hiện tại"
    
    # KHAI BÁO TRƯỚC thuộc tính sẽ dùng
    data: dict = Field(default_factory=dict, exclude=True)  # exclude=True để không serialize

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(PATH):
            try:
                with open(PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _run(self, user_id: str, top_k: int = 50) -> List[str]:
        if user_id not in self.data:
            return []
        neighbors = self.data[user_id]
        # Trả về list user_id giống nhất
        sorted_neighbors = sorted(neighbors.items(), key=lambda x: x[1], reverse=True)
        return [uid for uid, _ in sorted_neighbors[:top_k]]