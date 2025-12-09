# app/tools/graph_grouper.py
import networkx as nx
import pickle
import os
from langchain.tools import BaseTool
from pydantic import BaseModel
from typing import List, Dict

GRAPH_FILE = os.getenv("GRAPH_OUTPUT_FILE", "./data/book_graph.gpickle")


class GraphInput(BaseModel):
    product_ids: List[str]


class GraphGrouperTool(BaseTool):
    name: str = "smart_group_recommendations"
    description: str = (
        "Nhóm sách thông minh theo tác giả + thể loại + ngữ nghĩa từ graph"
    )

    def _run(self, product_ids: List[str]) -> List[Dict]:
        if not os.path.exists(GRAPH_FILE):
            return [{"title": "Gợi ý đặc biệt", "books": product_ids[:5]}]

        with open(GRAPH_FILE, "rb") as f:
            G = pickle.load(f)

        if not product_ids:
            return []

        subgraph = G.subgraph(product_ids).copy()
        groups = {}

        # 1. Nhóm theo tác giả (mạnh nhất)
        for node in subgraph.nodes():
            author = subgraph.nodes[node].get("author", "Khác")
            if author and author != "Khác":
                key = f"Sách của {author}"
                groups.setdefault(key, []).append(node)

        # 2. Nhóm theo thể loại (nếu chưa có trong nhóm tác giả)
        for node in subgraph.nodes():
            if any(node in books for books in groups.values()):
                continue
            cat = subgraph.nodes[node].get("category", "Khác")
            if cat and cat != "Khác":
                key = f"Thể loại {cat}"
                groups.setdefault(key, []).append(node)

        # 3. Nhóm semantic connected components (cực mạnh!)
        for cc in nx.connected_components(subgraph):
            component = list(cc)
            if len(component) < 3:
                continue
            if not any(component[0] in books for books in groups.values()):
                sample_names = [
                    subgraph.nodes[n].get("name", "")[:20]
                    for n in component[:2]
                    if subgraph.nodes[n].get("name")
                ]
                title = " & ".join(sample_names) + (
                    " và những cuốn tương tự"
                    if sample_names
                    else "Sách liên quan chặt chẽ"
                )
                groups[title] = component[:5]

        # 4. Fallback nhóm còn sót
        used = {book for books in groups.values() for book in books}
        remain = [pid for pid in product_ids if pid not in used][:5]
        if remain:
            groups["Đang hot cùng sở thích của bạn"] = remain

        # Format kết quả
        result = []
        for title, books in groups.items():
            if len(books) >= 2:
                result.append({"title": title, "books": books[:5]})
        return result[:4] or [{"title": "Khám phá ngay", "books": product_ids[:5]}]
