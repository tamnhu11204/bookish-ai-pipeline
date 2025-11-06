# app/chains/behavioral_chain.py
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.tools.user_history import UserHistoryTool
from app.tools.vector_aggregator import VectorAggregatorTool
from app.tools.semantic_retriever import SemanticRetrieverTool
from app.tools.graph_grouper import GraphGrouperTool

history_tool = UserHistoryTool()
vector_tool = VectorAggregatorTool()
retriever_tool = SemanticRetrieverTool()
grouper_tool = GraphGrouperTool()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

prompt = PromptTemplate.from_template(
    """
Dựa trên lịch sử: {history}
Gợi ý: {recommendations}
Nhóm: {groups}

Tạo 3 combo sách có tiêu đề và giải thích tự nhiên (tiếng Việt).
Trả về JSON:
[
  {{"title": "...", "reason": "...", "book_ids": [...]}}
]
"""
)

chain = (
    {"user_id": RunnablePassthrough()}
    | {"history": lambda x: history_tool.invoke({"user_id": x["user_id"]})}
    | {
        "product_ids": lambda x: list(
            set(
                x["history"]["summary"].get("viewed", [])
                + x["history"]["summary"].get("cart", [])
                + x["history"]["summary"].get("favorite", [])
                + x["history"]["summary"].get("purchased", [])
            )
        ),
        "history": lambda x: x["history"],
    }
    | {
        "user_vector": lambda x: (
            vector_tool.invoke({"product_ids": x["product_ids"]})
            if x["product_ids"]
            else None
        ),
        "history": lambda x: x["history"],
    }
    | {
        "recommendations": lambda x: (
            retriever_tool.invoke({"user_vector": x["user_vector"], "top_k": 20})
            if x["user_vector"]
            else []
        ),
        "history": lambda x: x["history"],
    }
    | {
        "groups": lambda x: grouper_tool.invoke({"product_ids": x["recommendations"]}),
        "recommendations": lambda x: x["recommendations"],
        "history": lambda x: x["history"],
    }
    | prompt
    | llm
    | (lambda x: x.content)
)
