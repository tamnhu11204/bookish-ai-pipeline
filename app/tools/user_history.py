# app/tools/user_history.py

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Type
from app.connect_db.mongo_client import user_events, orders
from bson import ObjectId

class UserHistoryInput(BaseModel):
    user_id: Optional[str] = None

class UserHistoryTool(BaseTool):
    name: str = "get_user_history"
    description: str = "Lấy lịch sử hành vi người dùng"
    args_schema: Type[BaseModel] = UserHistoryInput

    def _run(self, input_dict: Dict = None, **kwargs) -> Dict:
        user_id = (input_dict or kwargs).get("user_id")
        if not user_id:
            return {"summary": {}}

        try:
            uid = ObjectId(user_id)
        except:
            return {"summary": {}}

        interactions = []

        for e in user_events.find({"userId": uid}):
            interactions.append((str(e["productId"]), e["eventType"]))

        for o in orders.find({"user": uid}):
            for it in o.get("orderItems", []):
                interactions.append((str(it["product"]), "purchase"))

        summary = {
            "viewed": [p for p, a in interactions if a in ["view", "view_book"]],
            "cart": [p for p, a in interactions if a == "add_to_cart"],
            "favorite": [p for p, a in interactions if a == "favorite_add"],
            "compared": [p for p, a in interactions if a == "compare"],
            "purchased": [p for p, a in interactions if a == "purchase"],
        }

        return {"summary": summary}
