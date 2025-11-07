# app/chains/behavioral_chain.py
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.tools.user_history import UserHistoryTool
from app.tools.vector_aggregator import VectorAggregatorTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.tools.graph_grouper import GraphGrouperTool
import os
from dotenv import load_dotenv

# THÊM 2 DÒNG
from app.core.schemas import ComboResponse  # ← schema trên

load_dotenv()

history_tool = UserHistoryTool()
vector_tool = VectorAggregatorTool()
retriever_tool = SemanticRetrieverTool()
grouper_tool = GraphGrouperTool()

# THAY ĐỔI LLM → structured output
llm = ChatGroq(
    model="llama-3.3-70b-versatile", temperature=0.7, api_key=os.getenv("GROQ_API_KEY")
)

structured_llm = llm.with_structured_output(ComboResponse)  # ← BẮT BUỘC JSON

prompt = PromptTemplate.from_template(
    """
Bạn là chuyên gia gợi ý sách cho Bookish.

Dựa trên:
- Lịch sử người dùng: {history}
- Danh sách sách gợi ý: {recommendations}
- Các nhóm sách: {groups}

Hãy tạo đúng 3 combo sách.
Mỗi combo có:
- title: tiêu đề hấp dẫn
- reason: giải thích tự nhiên, gần gũi
- book_ids: 3-5 sách từ danh sách

Trả về đúng JSON, không thêm chữ nào khác.
"""
)

# Chain → dùng structured_llm thay llm
chain = (
    {"user_id": RunnablePassthrough()}
    | RunnableLambda(lambda x: print(f"[DEBUG] B1 - Input: {x['user_id']}") or x)
    | {"raw_history": lambda x: history_tool.invoke(x["user_id"])}
    | RunnableLambda(lambda x: print(f"[DEBUG] B1 - History: {x['raw_history']}") or x)
    | {
        "history": lambda x: x["raw_history"],
        "product_ids": lambda x: list(
            set(
                x["raw_history"]["summary"].get("viewed", [])
                + x["raw_history"]["summary"].get("cart", [])
                + x["raw_history"]["summary"].get("favorite", [])
                + x["raw_history"]["summary"].get("purchased", [])
            )
        ),
    }
    | RunnableLambda(lambda x: print(f"[DEBUG] B2 - IDs: {x['product_ids']}") or x)
    | {
        "user_vector": lambda x: (
            vector_tool.invoke({"product_ids": x["product_ids"]})
            if x["product_ids"]
            else None
        ),
        "history": lambda x: x["history"],
    }
    | RunnableLambda(
        lambda x: print(f"[DEBUG] B3 - Vector: {'OK' if x['user_vector'] else 'NONE'}")
        or x
    )
    | {
        "recommendations": lambda x: (
            retriever_tool.invoke({"user_vector": x["user_vector"], "top_k": 20})
            if x["user_vector"]
            else []
        ),
        "history": lambda x: x["history"],
    }
    | RunnableLambda(
        lambda x: print(f"[DEBUG] B4 - Recs: {len(x['recommendations'])}") or x
    )
    | {
        "groups": lambda x: grouper_tool.invoke({"product_ids": x["recommendations"]}),
        "recommendations": lambda x: x["recommendations"],
        "history": lambda x: x["history"],
    }
    | RunnableLambda(lambda x: print(f"[DEBUG] B5 - Groups: {x['groups']}") or x)
    | prompt
    | structured_llm
)
