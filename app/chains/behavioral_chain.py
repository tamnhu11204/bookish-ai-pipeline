# app/chains/behavioral_chain.py
from functools import lru_cache
import time
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.tools.user_history import UserHistoryTool
from app.tools.vector_aggregator import VectorAggregatorTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.tools.cache import get_cached_groups
from app.connect_db.mongo_client import products
from app.core.schemas import ComboResponse
from bson import ObjectId
import os

llm = ChatGroq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=os.getenv("GROQ_API_KEY")
)
structured_llm = llm.with_structured_output(ComboResponse)


@lru_cache(maxsize=10000)
def get_cat(pid: str) -> str:
    try:
        doc = products.find_one({"_id": ObjectId(pid)}, {"category.name": 1})
        return doc.get("category", {}).get("name", "") if doc else ""
    except:
        return ""


prompt = PromptTemplate.from_template(
    """
Bạn là chuyên gia curation sách hàng đầu Việt Nam.

DỮ LIỆU ĐẦU VÀO:
- Nhóm sách đã phân tích sẵn (BẮT BUỘC dùng nhóm này làm chủ đạo): 
{groups}

- Danh sách ID sách khả dụng (phải dùng ít nhất 90% từ đây, KHÔNG BỊA ID): 
{book_ids}

YÊU CẦU KHÔNG ĐƯỢC PHÁ VỠ:
→ Tạo ĐÚNG 2 combo
→ Mỗi combo PHẢI CÓ ĐÚNG 5 sách
→ Ưu tiên lấy nguyên 1 nhóm (5 sách từ cùng nhóm là đẹp nhất)
→ Nếu nhóm nào <5 sách thì bổ sung thêm từ danh sách sao cho đủ 5
→ Tiêu đề: 5-9 từ, gây tò mò hoặc chạm cảm xúc mạnh
→ Lý do: ngắn gọn, tự nhiên, thuyết phục
→ Tuyệt đối KHÔNG dùng từ: bán chạy, mới, nên đọc, phổ biến

Context bổ trợ: {context}

TRẢ VỀ ĐÚNG JSON SAU, KHÔNG THÊM CHỮ NÀO:

{{
  "combos": [
    {{"title": "string", "reason": "string", "book_ids": ["id1","id2","id3","id4","id5"]}},
    {{"title": "string", "reason": "string", "book_ids": ["id6","id7","id8","id9","id10"]}}
  ]]
}}
"""
)


def process_recommendations(x: dict) -> dict:
    # Lấy danh sách ID đã tương tác
    ids = x.get("ids", [])

    # Tính user vector
    vector = None
    if ids:
        vector = VectorAggregatorTool().invoke({"product_ids": ids})

    # Lấy category boost an toàn
    cats = []
    source_pids = (
        x["history"]["summary"].get("purchased", [])[:5]
        or x["history"]["summary"].get("favorite", [])[:5]
    )
    for pid in source_pids:
        cat = get_cat(pid)
        if cat and cat.strip() and cat != "Không rõ":
            cats.append(cat)

    # Tìm sách tương đồng
    recs = []
    if vector:
        try:
            recs = SemanticRetrieverTool().invoke(
                {
                    "user_vector": vector,
                    "top_k": 40,
                    "exclude_ids": x["history"]["summary"].get("purchased", [])[:20],
                    "category_boost": cats or None,
                }
            )
        except Exception as e:
            print(f"[BEHAVIORAL] Semantic search lỗi: {e}")

    # Fallback nếu không có kết quả
    if not recs:
        recs = ids[:10]

    return {**x, "recs": recs, "cats": cats}


behavioral_chain = (
    RunnableLambda(
        lambda x: {"user_id": x.get("user_id"), "session_id": x.get("session_id")}
    )
    | RunnableLambda(lambda x: {**x, "history": UserHistoryTool().invoke(x)})
    | RunnableLambda(
        lambda x: {
            **x,
            "ids": list(
                {
                    *x["history"]["summary"].get("viewed", []),
                    *x["history"]["summary"].get("cart", []),
                    *x["history"]["summary"].get("favorite", []),
                    *x["history"]["summary"].get("purchased", []),
                }
            ),
        }
    )
    | RunnableLambda(process_recommendations)
    | RunnableLambda(
        lambda x: {
            "groups": get_cached_groups(x["recs"]),
            "book_ids": ", ".join(x["recs"][:40]),
            "context": (
                f"Bạn đã tương tác với {len(x['ids'])} cuốn sách gần đây"
                + (
                    f", đặc biệt yêu thích thể loại: {', '.join(set(x.get('cats', [])))}"
                    if x.get("cats")
                    else ""
                )
            ),
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

__all__ = ["behavioral_chain"]
