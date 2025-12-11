# app/tools/graph_grouper.py
from bson import ObjectId
import networkx as nx
import pickle
import os
from langchain.tools import BaseTool
from pydantic import BaseModel
from typing import List, Dict
from app.connect_db.mongo_client import products

GRAPH_FILE = os.getenv("GRAPH_OUTPUT_FILE", "./data/book_graph.gpickle")


class GraphInput(BaseModel):
    product_ids: List[str]


class GraphGrouperTool(BaseTool):
    name: str = "smart_group_recommendations"
    description: str = (
        "Nhóm sách thông minh theo tác giả + thể loại + ngữ nghĩa từ graph"
    )

    def _run(self, product_ids: List[str]) -> List[Dict]:
        if not product_ids:
            return [{"title": "Khám phá thêm", "books": []}]

        if not os.path.exists(GRAPH_FILE):
            return [{"title": "Sách hay hôm nay", "books": product_ids[:5]}]

        with open(GRAPH_FILE, "rb") as f:
            G = pickle.load(f)

        subgraph = G.subgraph(product_ids).copy()
        if subgraph.number_of_nodes() == 0:
            return [{"title": "Gợi ý đặc biệt", "books": product_ids[:5]}]

        groups = {}

        # 1. Nhóm theo TÁC GIẢ (lấy tên thật)
        author_to_name = {}
        for node in subgraph.nodes():
            author_id = subgraph.nodes[node].get("author", "")
            if author_id and author_id != "Không rõ":
                if author_id not in author_to_name:
                    # Lấy tên thật từ MongoDB (cache để nhanh)
                    doc = products.find_one(
                        {"_id": ObjectId(author_id)}, {"authorName": 1}
                    )
                    author_to_name[author_id] = (
                        doc.get("authorName", "Nhiều tác giả")
                        if doc
                        else "Nhiều tác giả"
                    )
                author_name = author_to_name[author_id]
                groups.setdefault(f"Sách của {author_name}", []).append(node)

        # 2. Nhóm theo THỂ LOẠI
        for node in list(subgraph.nodes()):
            if any(node in books for books in groups.values()):
                continue
            cat = subgraph.nodes[node].get("category", "")
            if cat and cat != "Không rõ":
                groups.setdefault(f"Thể loại {cat}", []).append(node)

        # 3. Nhóm semantic (giữ nguyên)
        used = set()
        for title, books in list(groups.items()):
            used.update(books[:5])
            groups[title] = books[:5]

        remain = [n for n in product_ids if n not in used][:10]
        if remain:
            groups["Đang hot cùng sở thích"] = remain[:5]

        result = [
            {"title": title, "books": books}
            for title, books in groups.items()
            if len(books) >= 2
        ]
        return result or [
            {"title": "Gợi ý dành riêng cho bạn", "books": product_ids[:5]}
        ]
