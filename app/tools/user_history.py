# app/tools/user_history.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict
from app.connect_db.mongo_client import user_events, orders
from bson import ObjectId


class UserHistoryInput(BaseModel):
    user_id: str = Field(..., description="User ID (ObjectId hex)")


class UserHistoryTool(BaseTool):
    name: str = "get_user_behavior"
    description: str = "Lấy lịch sử hành vi người dùng từ MongoDB"
    args_schema: Type[BaseModel] = UserHistoryInput

    def _run(self, user_id: str) -> Dict:
        try:
            user_oid = ObjectId(user_id)
        except:
            return {"summary": {}}

        interactions = []
        for e in user_events.find({"userId": user_oid}):
            interactions.append(
                {"product_id": str(e["productId"]), "action": e["eventType"]}
            )
        for order in orders.find({"userId": user_oid}):
            for p in order.get("products", []):
                interactions.append(
                    {"product_id": str(p["productId"]), "action": "purchase"}
                )

        summary = {
            "viewed": list(
                {
                    i["product_id"]
                    for i in interactions
                    if i["action"] in ["view", "view_book"]
                }
            ),
            "cart": list(
                {i["product_id"] for i in interactions if i["action"] == "add_to_cart"}
            ),
            "favorite": list(
                {i["product_id"] for i in interactions if i["action"] == "favorite_add"}
            ),
            "compared": list(
                {i["product_id"] for i in interactions if i["action"] == "compare"}
            ),
            "purchased": list(
                {i["product_id"] for i in interactions if i["action"] == "purchase"}
            ),
        }
        return {"summary": summary}
