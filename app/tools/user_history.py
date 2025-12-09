# app/tools/user_history.py
# BẢN CUỐI CÙNG – ĐÃ FIX CẢ 2 LỖI CÙNG LÚC: ValidationError + missing argument
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Dict
from app.connect_db.mongo_client import user_events, orders
from bson import ObjectId


class UserHistoryInput(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID (ObjectId hex)")
    session_id: Optional[str] = Field(None, description="Session ID cho khách vãng lai")


class UserHistoryTool(BaseTool):
    name: str = "get_user_behavior"
    description: str = "Lấy lịch sử hành vi – hỗ trợ user_id hoặc session_id"
    args_schema: Type[BaseModel] = UserHistoryInput  # ← ĐÃ FIX Pydantic v2

    def _run(self, input_dict: Optional[Dict] = None, **kwargs) -> Dict:
        # SIÊU QUAN TRỌNG: HỖ TRỢ CẢ 2 CÁCH GỌI
        # 1. Gọi kiểu cũ: invoke({"user_id": "...", "session_id": "..."})
        # 2. Gọi kiểu mới: invoke(user_id="...", session_id="...")
        if input_dict is None:
            input_dict = kwargs  # nếu gọi bằng keyword args
        
        user_id = input_dict.get("user_id") if isinstance(input_dict, dict) else None
        session_id = input_dict.get("session_id") if isinstance(input_dict, dict) else None

        query = {}
        if user_id:
            try:
                query["userId"] = ObjectId(user_id)
            except:
                return {"summary": {}}
        elif session_id:
            query["sessionId"] = session_id
        else:
            return {"summary": {}}

        interactions = []
        for e in user_events.find(query):
            interactions.append({
                "product_id": str(e["productId"]),
                "action": e["eventType"]
            })

        if user_id and "userId" in query:
            for order in orders.find({"user": query["userId"]}):
                for p in order.get("products", []):
                    interactions.append({
                        "product_id": str(p["productId"]),
                        "action": "purchase"
                    })

        summary = {
            "viewed": list({i["product_id"] for i in interactions if i["action"] in ["view", "view_book"]}),
            "cart": list({i["product_id"] for i in interactions if i["action"] == "add_to_cart"}),
            "favorite": list({i["product_id"] for i in interactions if i["action"] == "favorite_add"}),
            "compared": list({i["product_id"] for i in interactions if i["action"] == "compare"}),
            "purchased": list({i["product_id"] for i in interactions if i["action"] == "purchase"}),
        }
        return {"summary": summary}