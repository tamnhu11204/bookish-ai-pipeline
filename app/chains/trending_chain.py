# app/chains/trending_chain.py
import time
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.tools.trending_news import TrendingNewsTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.connect_db.vector_db import get_model
import os
from app.core.schemas import ComboResponse
from app.tools.graph_grouper import GraphGrouperTool
import json
from app.tools.cache import get_cached_groups
from app.debug.debug_log import log_time

news_tool = TrendingNewsTool()
retriever = SemanticRetrieverTool()
llm = ChatGroq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=os.getenv("GROQ_API_KEY")
)
model = get_model()
structured_llm = llm.with_structured_output(ComboResponse)


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
    {{"title": "string", "reason": "string", "book_ids": {book_ids_example}}},
    {{"title": "string", "reason": "string", "book_ids": {book_ids_example}}}
  ]]
}}
"""
)

# ==================== TRENDING CHAIN HOÀN HẢO (DỰA TRÊN CODE CŨ CỦA BẠN) ====================
trending_chain = (
    RunnablePassthrough()
    | RunnableLambda(
        lambda x: print(f"[DEBUG TREND] Bắt đầu lấy tin tức trending...") or x
    )
    | RunnableLambda(lambda x: {"raw": news_tool.invoke({"top_k": 5})})
    | RunnableLambda(lambda x: print(f"[DEBUG TREND] Raw news: {x['raw']}") or x)
    | RunnableLambda(
        lambda x: {
            "topics": (
                "\n".join([f"- {t.get('topic', 'Chủ đề hot')}" for t in x["raw"]])
                if x["raw"]
                else "- Sách đang được quan tâm"
            ),
            "vectors": (
                [
                    model.encode(
                        t.get("topic", "sách hay"), normalize_embeddings=True
                    ).tolist()
                    for t in x["raw"]
                ]
                if x["raw"]
                else []
            ),
        }
    )
    | RunnableLambda(
        lambda x: {
            **x,
            "book_ids": list(
                set(
                    bid
                    for vec in x["vectors"]
                    for bid in retriever.invoke({"user_vector": vec, "top_k": 6})
                )
            )[
                :20
            ],  # Giới hạn 20 để nhanh
        }
    )
    | RunnableLambda(
        lambda x: print(f"[DEBUG TREND] Trending books: {len(x['book_ids'])} cuốn") or x
    )
    | RunnableLambda(
        lambda x: {
            "groups": get_cached_groups(x["book_ids"]),
            "book_ids": ", ".join(x["book_ids"]),
            "context": x.get("topics", "Sách đang hot theo tin tức hôm nay"),
        }
    )
    | RunnableLambda(
        lambda x: {
            **x,
            "book_ids_example": [
                bid.strip() for bid in x["book_ids"].split(",") if bid.strip()
            ][:15],
        }
    )
    | prompt
    | RunnableLambda(
        lambda x: (print(f"[DEBUG TRENDING] Gọi LLM lúc {time.time():.0f}"), x)[1]
    )
    | structured_llm
    | RunnableLambda(
        lambda x: (print(f"[DEBUG TRENDING] LLM trả về lúc {time.time():.0f}"), x)[1]
    )
)

__all__ = ["trending_chain"]
