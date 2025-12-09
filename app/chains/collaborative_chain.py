# app/chains/collaborative_chain.py
from langchain_core.runnables import RunnableLambda, RunnableBranch, RunnableParallel
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from app.core.schemas import ComboResponse
from app.tools.user_history import UserHistoryTool
from app.tools.user_similarity_tool import UserSimilarityTool
from app.connect_db.mongo_client import orders
from bson import ObjectId

# ==================== LLM & TOOLS ====================
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
structured_llm = llm.with_structured_output(ComboResponse)

history_tool = UserHistoryTool()
similarity_tool = UserSimilarityTool()

# ==================== HÀM LẤY TOP SÁCH BÁN CHẠY ====================
def get_top_selling_book_ids(limit: int = 10) -> str:
    try:
        pipeline = [
            {"$unwind": "$orderItems"},
            {"$group": {"_id": "$orderItems.product", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit + 5}
        ]
        results = list(orders.aggregate(pipeline))
        ids = [str(item["_id"]) for item in results if item["_id"]]
        return ", ".join(ids[:limit]) if ids else "101,202,303,404,505,606,707,808,909,1010"
    except:
        return "101,202,303,404,505,606,707,808,909,1010"

# ==================== PROMPT ====================
prompt = PromptTemplate.from_template("""
Bạn là chuyên gia gợi ý sách theo phong cách "Người giống bạn đã mua gì?".

Người dùng này có hành vi:
• Đã mua: {purchased_count} sách
• Đã xem: {viewed_count} sách
• Yêu thích: {favorite_count} cuốn
• So sánh: {compared_count} lần
• Giỏ hàng: {cart_count} sản phẩm

50 người có hành vi TƯƠNG ĐỒNG NHẤT đã mua các sách sau (ID): {rec_ids}

Hãy tạo đúng 3 combo cực kỳ hấp dẫn với:
- title: dưới 6 từ, cuốn hút
- reason: tự nhiên, kiểu "Người giống bạn thường mua thêm...", "Fan cùng gu hay chọn..."
- book_ids: 2–4 ID từ danh sách trên

Trả về JSON list duy nhất.
""")

# ==================== HÀM LẤY GỢI Ý TỪ USER GIỐNG (CÓ HỖ TRỢ session_id) ====================
def get_recommendations(x: dict) -> dict:
    user_id = x.get("user_id")
    session_id = x.get("session_id")
    summary = x["history"]["summary"]
    
    # Loại sách đã tương tác
    already_interacted = (
        set(summary.get("purchased", [])) |
        set(summary.get("viewed", []))
    )
    
    # Tìm user giống nhất – tool đã hỗ trợ cả user_id và session_id
    similar_user_ids = similarity_tool.invoke({
        "user_id": user_id,
        "session_id": session_id
    })[:40]
    
    rec_ids = set()

    for sim_uid in similar_user_ids:
        try:
            uid_obj = ObjectId(sim_uid)
            for order in orders.find({"user": uid_obj}).limit(3):
                for item in order.get("orderItems", []):
                    pid = str(item.get("product"))
                    if pid and pid not in already_interacted and pid not in rec_ids:
                        rec_ids.add(pid)
                        if len(rec_ids) >= 35:
                            break
                if len(rec_ids) >= 35: break
            if len(rec_ids) >= 35: break
        except: continue

    return {
        "purchased_count": len(summary.get("purchased", [])),
        "viewed_count": len(summary.get("viewed", [])),
        "favorite_count": len(summary.get("favorite", [])),
        "compared_count": len(summary.get("compared", [])),
        "cart_count": len(summary.get("cart", [])),
        "rec_ids": ", ".join(list(rec_ids)[:30]) if rec_ids else get_top_selling_book_ids()
    }

# ==================== CHAIN THẬT ====================
real_chain = (
    # Input có thể là {"user_id": "..."} hoặc {"session_id": "..."}
    RunnableLambda(lambda x: {
        "user_id": x.get("user_id"),
        "session_id": x.get("session_id")
    })
    | RunnableLambda(lambda x: {
        "history": UserHistoryTool().invoke({
            "user_id": x["user_id"],
            "session_id": x["session_id"]
        })
    })
    | RunnableLambda(lambda x: {**x, **get_recommendations(x)})
    | prompt
    | structured_llm
)

# ==================== FALLBACK CHO USER MỚI HOẶC KHÁCH VÃNG LAI CHƯA CÓ DỮ LIỆU ====================
fallback_chain = RunnableLambda(lambda x: {
    "purchased_count": 0, "viewed_count": 0, "favorite_count": 0,
    "compared_count": 0, "cart_count": 0,
    "rec_ids": get_top_selling_book_ids(10)
}) | prompt | structured_llm

# ==================== CHAIN CUỐI – TỰ ĐỘNG CHỌN ====================
collaborative_chain = (
    RunnableLambda(lambda x: x)
    | RunnableBranch(
        # Nếu có ít nhất 3 tương tác (dù là user hay session)
        (lambda x: len(
            x.get("history", {}).get("summary", {}).get("purchased", []) +
            x.get("history", {}).get("summary", {}).get("viewed", [])
        ) >= 3, real_chain),
        fallback_chain
    )
)

__all__ = ["collaborative_chain"]