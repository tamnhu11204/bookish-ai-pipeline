# app/chains/behavioral_chain.py
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate  # ← THÊM
from app.tools.user_history import UserHistoryTool
from app.tools.vector_aggregator import VectorAggregatorTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.tools.graph_grouper import GraphGrouperTool
from app.connect_db.mongo_client import products
from app.core.schemas import ComboResponse
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


# ← DÙNG PromptTemplate
prompt = PromptTemplate.from_template(
    "Dựa trên lịch sử: {history}\n"
    "Danh sách gợi ý: {recs}\n"
    "Nhóm sách (JSON): {groups}\n\n"
    "Tạo đúng 3 combo sách (title, reason, 3-5 book_ids)."
)

chain = (
    {"user_id": RunnablePassthrough()}
    | RunnableLambda(lambda x: {"history": UserHistoryTool().invoke(x["user_id"])})
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
    # ← CHUYỂN groups → str
    | RunnableLambda(
        lambda x: {
            **x,
            "groups": json.dumps(x["raw_groups"], ensure_ascii=False, indent=2),
        }
    )
    | prompt  # ← DÙNG PromptTemplate
    | structured_llm
)
