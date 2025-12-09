# app/chains/behavioral_chain.py
import time
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.tools.user_history import UserHistoryTool
from app.tools.vector_aggregator import VectorAggregatorTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.tools.graph_grouper import GraphGrouperTool
from app.connect_db.mongo_client import products
from app.core.schemas import ComboResponse
from app.tools.cache import get_cached_groups
from app.debug.debug_log import log_time
from bson import ObjectId
import os
import json

llm = ChatGroq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=os.getenv("GROQ_API_KEY")
)
structured_llm = llm.with_structured_output(ComboResponse)


def get_cat(pid):
    doc = products.find_one({"_id": ObjectId(pid)}, {"category.name": 1})
    return doc.get("category", {}).get("name", "") if doc else ""


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

# ĐÃ SỬA HOÀN CHỈNH – KHÔNG CÒN TRUYỀN OBJECT NỮA!
chain = (
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
    | RunnableLambda(
        lambda x: {
            "ids": list(
                {
                    *x["history"]["summary"].get("viewed", []),
                    *x["history"]["summary"].get("cart", []),
                    *x["history"]["summary"].get("favorite", []),
                    *x["history"]["summary"].get("purchased", []),
                }
            ),
            "history": x["history"],
        }
    )
    | RunnableLambda(
        lambda x: {
            "vector": (
                VectorAggregatorTool().invoke({"product_ids": x["ids"]})
                if x["ids"]
                else None
            ),
            "history": x["history"],
        }
    )
    | RunnableLambda(
        lambda x: {
            "recs": (
                SemanticRetrieverTool().invoke(
                    {
                        "user_vector": x["vector"],
                        "top_k": 20,
                        "exclude_ids": x["history"]["summary"].get("purchased", [])
                        + x["history"]["summary"].get("viewed", [])[-5:],
                        "category_boost": [
                            get_cat(p)
                            for p in (
                                x["history"]["summary"].get("purchased", [])[:3]
                                or x["history"]["summary"].get("favorite", [])[:3]
                            )
                        ],
                    }
                )
                if x["vector"]
                else []
            ),
            "history": x["history"],
        }
    )
    | RunnableLambda(
        lambda x: {
            "raw_groups": GraphGrouperTool().invoke({"product_ids": x["recs"]}),
            "recs": x["recs"],
            "history": x["history"],
        }
    )
    | RunnableLambda(
        lambda x: {
            **x,
            "groups": json.dumps(x["raw_groups"], ensure_ascii=False, indent=2),
        }
    )
    | prompt
    | RunnableLambda(
        lambda x: (print(f"[DEBUG BEHAVIORAL] Gọi LLM lúc {time.time():.0f}"), x)[1]
    )
    | structured_llm
    | RunnableLambda(
        lambda x: (print(f"[DEBUG BEHAVIORAL] LLM trả về lúc {time.time():.0f}"), x)[1]
    )
)

behavioral_chain = chain
__all__ = ["behavioral_chain"]
