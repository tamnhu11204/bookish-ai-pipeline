# app/chains/collaborative_chain.py

from collections import defaultdict
from bson import ObjectId
from langchain_core.runnables import RunnableLambda, RunnableBranch
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from app.core.schemas import ComboResponse
from app.tools.user_history import UserHistoryTool
from app.tools.user_similarity_tool import UserSimilarityTool
from app.tools.cache import get_cached_groups
from app.connect_db.mongo_client import orders
import os

# ================= INIT =================
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY"),
)
structured_llm = llm.with_structured_output(ComboResponse)

history_tool = UserHistoryTool()
similarity_tool = UserSimilarityTool()

TOP_SIM_USERS = 40
TOP_BOOKS = 30
MAX_ORDER_PER_USER = 3

# ================= TOP SELLING (COLD START) =================
def get_top_selling_book_ids(limit: int = 10) -> str:
    pipeline = [
        {"$unwind": "$orderItems"},
        {"$group": {"_id": "$orderItems.product", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    try:
        ids = [str(i["_id"]) for i in orders.aggregate(pipeline)]
        return ", ".join(ids)
    except:
        return ""

# ================= PROMPT =================
prompt = PromptTemplate.from_template(
    """
Bạn là chuyên gia curation sách hàng đầu Việt Nam.

DỮ LIỆU ĐẦU VÀO:
- Nhóm sách đã phân tích sẵn:
{groups}

- Danh sách ID sách khả dụng:
{book_ids}

YÊU CẦU:
→ Tạo ĐÚNG 2 combo
→ Mỗi combo ĐÚNG 5 sách
→ Ưu tiên lấy nguyên nhóm
→ Tiêu đề 5–9 từ
→ Lý do ngắn gọn, tự nhiên
→ KHÔNG dùng từ: bán chạy, mới, nên đọc, phổ biến

Context: {context}

TRẢ VỀ ĐÚNG JSON
"""
)

# ================= USER-TO-USER RECOMMEND =================
def get_recommendations(x: dict) -> dict:
    user_id = x.get("user_id")
    summary = x["history"]["summary"]

    already = set().union(
        summary.get("viewed", []),
        summary.get("cart", []),
        summary.get("favorite", []),
        summary.get("compared", []),
        summary.get("purchased", []),
    )

    similar_users = similarity_tool.invoke(
        {"user_id": user_id, "top_k": TOP_SIM_USERS}
    )

    scores = defaultdict(float)

    for suid in similar_users:
        try:
            uid = ObjectId(suid)
            for order in orders.find({"user": uid}).limit(MAX_ORDER_PER_USER):
                for it in order.get("orderItems", []):
                    pid = str(it.get("product"))
                    if pid and pid not in already:
                        scores[pid] += 1.0
        except:
            continue

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    book_ids = [pid for pid, _ in ranked[:TOP_BOOKS]]

    if not book_ids:
        book_ids = get_top_selling_book_ids(TOP_BOOKS).split(",")

    return {
        "rec_ids": ", ".join(book_ids),
    }

# ================= FINAL CHAIN =================
collaborative_chain = (
    RunnableLambda(lambda x: {"user_id": x.get("user_id")})
    | RunnableLambda(lambda x: {**x, "history": history_tool.invoke(x)})
    | RunnableBranch(
        (
            lambda x: len(x["history"]["summary"].get("purchased", [])) >= 3,
            RunnableLambda(lambda x: {**x, **get_recommendations(x)})
            | RunnableLambda(
                lambda x: {
                    "groups": get_cached_groups(x["rec_ids"].split(",")),
                    "book_ids": x["rec_ids"],
                    "context": "Những độc giả có sở thích giống bạn thường chọn các sách sau",
                }
            )
            | prompt
            | structured_llm,
        ),
        RunnableLambda(
            lambda _: {
                "groups": get_cached_groups([]),
                "book_ids": get_top_selling_book_ids(20),
                "context": "Gợi ý dành cho người mới bắt đầu đọc sách",
            }
        )
        | prompt
        | structured_llm,
    )
)

__all__ = ["collaborative_chain"]
