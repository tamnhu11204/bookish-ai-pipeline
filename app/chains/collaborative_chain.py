# app/chains/collaborative_chain.py

import time
from bson import ObjectId
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableLambda,
    RunnableBranch,
    RunnableParallel,
)
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from app.core.schemas import ComboResponse
from app.tools.user_history import UserHistoryTool
from app.tools.collaborative_tool import CollaborativeFilteringTool
from app.tools.graph_grouper import GraphGrouperTool
import json
from app.tools.cache import get_cached_groups
from app.debug.debug_log import log_time
from app.connect_db.mongo_client import orders
from app.tools.user_similarity_tool import UserSimilarityTool
import os

# ==================== INIT ====================
llm = ChatGroq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=os.getenv("GROQ_API_KEY")
)
structured_llm = llm.with_structured_output(ComboResponse)

history_tool = UserHistoryTool()
collab_tool = CollaborativeFilteringTool()
similarity_tool = UserSimilarityTool()


# ==================== HÀM LẤY TOP SÁCH BÁN CHẠY ====================
def get_top_selling_book_ids(limit: int = 10) -> str:
    try:
        pipeline = [
            {"$unwind": "$orderItems"},
            {"$group": {"_id": "$orderItems.product", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit + 5},
        ]
        results = list(orders.aggregate(pipeline))
        ids = [str(item["_id"]) for item in results if item["_id"]]
        return (
            ", ".join(ids[:limit])
            if ids
            else "101,202,303,404,505,606,707,808,909,1010"
        )
    except:
        return "101,202,303,404,505,606,707,808,909,1010"


# ==================== PROMPT SIÊU ĐỈNH ====================
prompt = PromptTemplate.from_template(
    """
Bạn là chuyên gia curation sách hàng đầu Việt Nam.

DỮ LIỆU ĐẦU VÀO:
- Nhóm sách đã phân tích sẵn (BẮT BUỘC dùng nhóm này làm chủ đạo): 
{groups}

- Danh sách ID sách khả dụng (phải dùng ít nhất 90% từ đây): 
{book_ids}

YÊU CẦU KHÔNG ĐƯỢC PHÁ VỠ:
→ Tạo ĐÚNG 2 combo
→ Mỗi combo PHẢI CÓ ĐÚNG 5 sách (không hơn, không kém)
→ Ưu tiên lấy nguyên 1 nhóm (5 sách từ cùng nhóm là đẹp nhất)
→ Nếu nhóm nào <5 sách thì bổ sung thêm từ danh sách sao cho đủ 5
→ Tiêu đề: 5-9 từ, gây tò mò hoặc chạm cảm xúc mạnh
→ Lý do: ngắn gọn, tự nhiên, thuyết phục
→ Tuyệt đối KHÔNG dùng từ: bán chạy, mới, nên đọc, phổ biến

Context bổ trợ: {context}

Trả về đúng format JSON sau, không thêm bất kỳ chữ nào khác:

{{
  "combos": [
    {{
      "title": "string",
      "reason": "string",
      "book_ids": ["id1", "id2", "id3", "id4", "id5"]
    }},
    {{
      "title": "string",
      "reason": "string",
      "book_ids": ["id6", "id7", "id8", "id9", "id10"]
    }}
  ]]
}}
"""
)


# ==================== HÀM LẤY GỢI Ý TỪ USER GIỐNG (CÓ HỖ TRỢ session_id) ====================
def get_recommendations(x: dict) -> dict:
    user_id = x.get("user_id")
    session_id = x.get("session_id")
    summary = x["history"]["summary"]

    # Loại sách đã tương tác
    already_interacted = set(summary.get("purchased", [])) | set(
        summary.get("viewed", [])
    )

    # Tìm user giống nhất – tool đã hỗ trợ cả user_id và session_id
    similar_user_ids = similarity_tool.invoke(
        {"user_id": user_id, "session_id": session_id}
    )[:40]

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
                if len(rec_ids) >= 35:
                    break
            if len(rec_ids) >= 35:
                break
        except:
            continue

    return {
        "purchased_count": len(summary.get("purchased", [])),
        "viewed_count": len(summary.get("viewed", [])),
        "favorite_count": len(summary.get("favorite", [])),
        "compared_count": len(summary.get("compared", [])),
        "cart_count": len(summary.get("cart", [])),
        "rec_ids": (
            ", ".join(list(rec_ids)[:30]) if rec_ids else get_top_selling_book_ids()
        ),
    }


# ==================== CHAIN THẬT ====================
real_chain = (
    # Input có thể là {"user_id": "..."} hoặc {"session_id": "..."}
    RunnableLambda(
        lambda x: {"user_id": x.get("user_id"), "session_id": x.get("session_id")}
    )
    | RunnableLambda(
        lambda x: {
            "history": UserHistoryTool().invoke(
                {"user_id": x["user_id"], "session_id": x["session_id"]}
            )
        }
    )
    | RunnableLambda(lambda x: {**x, **get_recommendations(x)})
    | prompt
    | RunnableLambda(
        lambda x: (print(f"[DEBUG CF] Gọi LLM lúc {time.time():.0f}"), x)[1]
    )
    | structured_llm
    | RunnableLambda(
        lambda x: (print(f"[DEBUG CF] LLM trả về lúc {time.time():.0f}"), x)[1]
    )
)

# ==================== CHAIN FALLBACK (user mới) ====================
fallback_chain = (
    {"user_id": lambda x: x}
    | RunnableLambda(
        lambda x: {
            "purchased_count": 0,
            "viewed_count": 0,
            "favorite_count": 0,
            "compared_count": 0,
            "cart_count": 0,
            "rec_ids": get_top_selling_book_ids(10),
        }
    )
    | prompt
    | structured_llm
)

# ==================== CHAIN CUỐI: TỰ ĐỘNG CHỌN ĐÚNG ĐƯỜNG  ====================
collaborative_chain = (
    {"user_id": lambda x: x}
    | RunnableParallel(
        {
            "user_id": lambda x: x["user_id"],
            "history": lambda x: history_tool.invoke(x["user_id"]),
        }
    )
    | RunnableBranch(
        # Điều kiện kiểm tra: đã có history rồi → mới được truy cập summary
        (
            lambda x: len(
                x["history"]["summary"].get("purchased", [])
                + x["history"]["summary"].get("viewed", [])
            )
            >= 3,
            real_chain,
        ),
        fallback_chain,
    )
)

__all__ = ["collaborative_chain"]
