# app/tools/graph_grouper.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List, Dict
import networkx as nx
import pickle
import os

GRAPH_FILE = os.getenv("GRAPH_OUTPUT_FILE", "./data/book_graph.gpickle")


class GraphInput(BaseModel):
    product_ids: List[str]


class GraphGrouperTool(BaseTool):
    name: str = "group_recommendations"
    description: str = "Nhóm sách theo tác giả từ graph"
    args_schema: Type[BaseModel] = GraphInput

    def _run(self, product_ids: List[str]) -> List[Dict]:
        if not os.path.exists(GRAPH_FILE):
            return []
        with open(GRAPH_FILE, "rb") as f:
            G = pickle.load(f)
        groups = {}
        for pid in product_ids:
            if pid in G:
                author = G.nodes[pid].get("author", "Khác")
                groups.setdefault(author, []).append(pid)
        return [
            {
                "title": f"Sách của {author}" if author != "Khác" else "Gợi ý khác",
                "books": v[:5],
            }
            for author, v in groups.items()
        ]
