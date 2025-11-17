# app/chains/collaborative_chain.py
import os
import json
import sys
from dotenv import load_dotenv
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from app.core.schemas import ComboResponse

# FIX PATH
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()

# IMPORT TOOLS
from app.tools.user_history import UserHistoryTool
from app.tools.collaborative_tool import CollaborativeFilteringTool

# INIT
history_tool = UserHistoryTool()
collab_tool = CollaborativeFilteringTool()

llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY"),
)
structured_llm = llm.with_structured_output(ComboResponse)

prompt = PromptTemplate.from_template(
    """
Lịch sử người dùng: {history_summary}
Gợi ý cộng tác (danh sách ID): {collab_recs}

Tạo đúng 3 combo sách:
- title: <6 từ
- reason: tự nhiên
- book_ids: 2-4 ID

Trả về JSON list.
"""
)

# BUILD CHAIN
collab_chain = (
    {"user_id": RunnablePassthrough()}
    | RunnableLambda(lambda x: print(f"[DEBUG CF] User: {x['user_id']}") or x)
    | {"raw_history": lambda x: history_tool.invoke(x["user_id"])}
    | {
        "history_summary": lambda x: x["raw_history"].get("summary", {}),
        "product_ids": lambda x: list(
            set(
                x["raw_history"]["summary"].get("purchased", [])
                + x["raw_history"]["summary"].get("viewed", [])
                + x["raw_history"]["summary"].get("cart", [])
                + x["raw_history"]["summary"].get("favorite", [])
            )
        ),
    }
    | RunnableLambda(lambda x: print(f"[DEBUG CF] IDs: {len(x['product_ids'])}") or x)
    | {
        "raw_collab": lambda x: (
            collab_tool.invoke({"product_ids": x["product_ids"]})
            if x["product_ids"]
            else []
        ),
        "history_summary": lambda x: x["history_summary"],
    }
    | RunnableLambda(lambda x: print(f"[DEBUG CF] Raw collab: {x['raw_collab']}") or x)
    | RunnableLambda(
        lambda x: {
            **x,
            "collab_recs": json.dumps(
                [item["book_id"] for item in x["raw_collab"]], ensure_ascii=False
            ),
        }
    )
    | prompt
    | structured_llm
)

# EXPORT
__all__ = ["collab_chain"]
