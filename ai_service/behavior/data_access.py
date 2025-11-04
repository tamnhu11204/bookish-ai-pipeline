# data_access.py
import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    exit()

# Các collection
user_events = db["userevents"]
orders = db["orders"]
products = db["products"]

# ==============================
# Hàm: Lấy hành vi người dùng
# ==============================
def get_user_interactions(user_id: str):
    """
    Trả về tất cả hành vi của người dùng:
    - view / view_book
    - add_to_cart
    - favorite_add / favorite_remove
    - compare
    - purchase (lấy từ orders)
    """
    if not user_id:
        return {"user_id": None, "interactions": [], "note": "anonymous_session"}

    user_oid = ObjectId(user_id)

    # --- 1. Lấy hành vi từ UserEvent ---
    events = list(user_events.find({"userId": user_oid}))
    interactions = []

    for e in events:
        interactions.append({
            "product_id": str(e.get("productId")),
            "action": e.get("eventType"),
            "timestamp": e.get("timestamp")
        })

    # --- 2. Lấy sản phẩm đã mua từ Order ---
    user_orders = list(orders.find({"userId": user_oid}))
    for order in user_orders:
        for p in order.get("products", []):
            interactions.append({
                "product_id": str(p.get("productId")),
                "action": "purchase",
                "timestamp": order.get("createdAt")
            })

    # --- 3. Trường hợp người dùng mới ---
    if not interactions:
        return {"user_id": user_id, "interactions": [], "note": "new_user_no_activity"}

    # --- 4. Gom nhóm theo loại hành vi ---
    summary = {
        "viewed": list({i["product_id"] for i in interactions if i["action"] in ["view", "view_book"]}),
        "cart": list({i["product_id"] for i in interactions if i["action"] == "add_to_cart"}),
        "favorite": list({i["product_id"] for i in interactions if i["action"].startswith("favorite")}),
        "compared": list({i["product_id"] for i in interactions if i["action"] == "compare"}),
        "purchased": list({i["product_id"] for i in interactions if i["action"] == "purchase"}),
    }

    return {
        "user_id": user_id,
        "interactions": interactions,
        "summary": summary
    }

# ==============================
# Hàm test nhanh
# ==============================
if __name__ == "__main__":
    test_user = "6868164751471f57737434d5"
    result = get_user_interactions(test_user)
    print("\n🎯 User interactions summary:")
    for key, value in result["summary"].items():
        print(f"- {key}: {len(value)} items")
    print("\nExample interactions:")
    for item in result["interactions"][:5]:
        print(item)
