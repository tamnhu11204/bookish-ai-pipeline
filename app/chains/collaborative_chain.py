# app/chains/collaborative_chain.py
import os
from dotenv import load_dotenv
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
import os

# THÊM 2 DÒNG NÀY
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# =========================
# IMPORT TOOLS
# =========================
from app.tools.user_history import UserHistoryTool
from app.tools.collaborative_tool import CollaborativeFilteringTool  # tên file đúng

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# INIT TOOLS
# =========================
history_tool = UserHistoryTool()
collab_tool = CollaborativeFilteringTool()

# =========================
# INIT LLM
# =========================
GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.7,
    api_key=GROQ_KEY
) if GROQ_KEY else None

# =========================
# PROMPT
# =========================
prompt = PromptTemplate.from_template(
    """
Bạn là chuyên gia gợi ý sách tại Bookish.

Lịch sử người dùng: {history_summary}
Gợi ý cộng tác: {collab_recs}

Tạo đúng 3 combo sách:
- Mỗi combo: 2–4 sách
- title: hấp dẫn
- reason: giải thích tự nhiên (ví dụ: "nhiều người mua X cũng thích Y")
- book_ids: danh sách ID

Trả về đúng JSON, không thêm chữ.
"""
)

# =========================
# BUILD CHAIN (LCEL CHUẨN)
# =========================
chain = (
    {"user_id": RunnablePassthrough()}
    | RunnableLambda(lambda x: print(f"[DEBUG CF] User: {x['user_id']}") or x)
    | {"raw_history": lambda x: history_tool.invoke(x["user_id"])}
    | {
        "history_summary": lambda x: x["raw_history"].get("summary", {}),
        "product_ids": lambda x: list(set(
            x["raw_history"]["summary"].get("purchased", []) +
            x["raw_history"]["summary"].get("viewed", []) +
            x["raw_history"]["summary"].get("cart", []) +
            x["raw_history"]["summary"].get("favorite", [])
        )),
    }
    | RunnableLambda(lambda x: print(f"[DEBUG CF] IDs: {len(x['product_ids'])}") or x)
    | {
        "collab_recs": lambda x: collab_tool.invoke(x["product_ids"]) if x["product_ids"] else [],
        "history_summary": lambda x: x["history_summary"],
    }
    | RunnableLambda(lambda x: print(f"[DEBUG CF] Recs: {len(x['collab_recs'])}") or x)
    | prompt
    | llm
)

# EXPORT CHAIN ĐỂ IMPORT Ở NƠI KHÁC
collab_chain = chain  # ĐÂY LÀ DÒNG BẠN THIẾU!

# =========================
# API ROUTER
# =========================
router = APIRouter()

class RecommendRequest(BaseModel):
    user_id: str

