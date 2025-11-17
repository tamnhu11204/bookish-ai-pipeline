# app/chains/trending_chain.py
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.tools.trending_news import TrendingNewsTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.connect_db.vector_db import get_model
import os
from app.core.schemas import ComboResponse

# ... (phần khởi tạo không đổi) ...
news_tool = TrendingNewsTool()
retriever = SemanticRetrieverTool()
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.6,
    api_key=os.getenv("GROQ_API_KEY"),
)
model = get_model()
structured_llm = llm.with_structured_output(ComboResponse)


# SỬA: Xóa phần "Ví dụ" khỏi prompt để tránh LLM sao chép.
prompt = PromptTemplate.from_template(
    """
Bạn là một chuyên gia gợi ý sách thông minh, chuyên tạo ra các combo sách hấp dẫn dựa trên các chủ đề đang thịnh hành.

Dưới đây là các chủ đề đang hot trong 24 giờ qua:
{topics}

Dựa vào danh sách các ID sách liên quan được cung cấp: {book_ids}

**Yêu cầu của bạn là:**
1.  Tạo ra chính xác 3 combo sách độc đáo.
2.  Mỗi combo phải có một **tiêu đề (title)** thật ngắn gọn và thu hút (dưới 6 từ).
3.  Mỗi combo phải có một **lý do gợi ý (reason)** tự nhiên, thuyết phục (1-2 câu).
4.  Mỗi combo phải chứa từ **3 đến 5 ID sách** từ danh sách đã cho.
5.  **QUAN TRỌNG:** Chỉ sử dụng các ID sách từ danh sách `{book_ids}` được cung cấp. Không được tự bịa ra ID.
6.  Trả về kết quả dưới dạng một danh sách JSON (JSON list) các combo.
"""
)

trending_chain = (
    {"raw": lambda _: news_tool.invoke({"top_k": 3})}
    | RunnableLambda(
        lambda x: {
            "topics": "\n".join([f"- {t['topic']}" for t in x["raw"]]),
            "vectors": [
                model.encode(t["topic"], normalize_embeddings=True).tolist()
                for t in x["raw"]
            ],
        }
    )
    | RunnableLambda(
        lambda x: {
            "topics": x["topics"],
            "book_ids": list(
                set(  # Dùng set để loại bỏ các ID trùng lặp
                    bid
                    for vec in x["vectors"]
                    for bid in retriever.invoke({"user_vector": vec, "top_k": 6})
                )
            )[:15],
        }
    )
    | prompt
    | structured_llm
)
