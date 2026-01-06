from bson import ObjectId
import networkx as nx
import pickle
import os
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.connect_db.mongo_client import products

GRAPH_FILE = os.getenv("GRAPH_OUTPUT_FILE", "./data/book_graph.gpickle")


class GraphInput(BaseModel):
    product_ids: List[str]


class GraphGrouperTool(BaseTool):
    name: str = "smart_group_recommendations"
    description: str = (
        "Nhóm sách thông minh theo tác giả + thể loại + ngữ nghĩa từ graph"
    )

    # Sử dụng Class Variable để lưu trữ Graph trong RAM (Singleton)
    _cached_graph: Optional[nx.Graph] = None
    _author_name_cache: Dict[str, str] = {}

    def _load_graph(self):
        """Hàm nội bộ để nạp Graph vào RAM một lần duy nhất"""
        if GraphGrouperTool._cached_graph is None:
            if os.path.exists(GRAPH_FILE):
                try:
                    with open(GRAPH_FILE, "rb") as f:
                        GraphGrouperTool._cached_graph = pickle.load(f)
                    print(
                        f"[SUCCESS] Đã nạp Graph vào RAM: {len(GraphGrouperTool._cached_graph)} nodes"
                    )
                except Exception as e:
                    print(f"[ERROR] Không thể nạp Graph: {e}")
            else:
                print(f"[WARNING] File Graph không tồn tại tại: {GRAPH_FILE}")
        return GraphGrouperTool._cached_graph

    def _get_author_name(self, author_id: str) -> str:
        """Lấy tên tác giả từ Cache hoặc MongoDB"""
        if not author_id or author_id == "Không rõ":
            return "Nhiều tác giả"

        # Kiểm tra trong RAM cache trước
        if author_id in GraphGrouperTool._author_name_cache:
            return GraphGrouperTool._author_name_cache[author_id]

        # Nếu không có mới gọi MongoDB
        try:
            doc = products.find_one({"_id": ObjectId(author_id)}, {"authorName": 1})
            name = doc.get("authorName", "Nhiều tác giả") if doc else "Nhiều tác giả"
            GraphGrouperTool._author_name_cache[author_id] = name  # Lưu vào cache
            return name
        except:
            return "Nhiều tác giả"

    def _run(self, product_ids: List[str]) -> List[Dict]:
        if not product_ids:
            return [{"title": "Khám phá thêm", "books": []}]

        # 1. Lấy Graph từ RAM
        G = self._load_graph()

        # Fallback nếu Graph không khả dụng
        if G is None:
            return [{"title": "Sách hay dành cho bạn", "books": product_ids[:5]}]

        # 2. Tạo subgraph siêu nhanh từ các node tồn tại
        valid_ids = [pid for pid in product_ids if pid in G]
        if not valid_ids:
            return [{"title": "Gợi ý đặc biệt", "books": product_ids[:5]}]

        subgraph = G.subgraph(valid_ids)
        groups = {}

        # 3. Nhóm theo TÁC GIẢ
        for node in subgraph.nodes():
            author_id = subgraph.nodes[node].get("author", "")
            if author_id and author_id != "Không rõ":
                # Lấy tên tác giả (ưu tiên cache)
                author_name = self._get_author_name(author_id)
                groups.setdefault(f"Sách của {author_name}", []).append(node)

        # 4. Nhóm theo THỂ LOẠI
        for node in subgraph.nodes():
            # Nếu sách đã được xếp vào nhóm tác giả rồi thì thôi (tránh trùng)
            if any(node in books for books in groups.values()):
                continue

            cat = subgraph.nodes[node].get("category", "")
            if cat and cat != "Không rõ":
                groups.setdefault(f"Chủ đề {cat}", []).append(node)

        # 5. Xử lý kết quả & Nhóm Semantic (Phần còn lại)
        used = set()
        final_groups = []

        # Ưu tiên các nhóm có trên 2 cuốn
        for title, books in groups.items():
            valid_books = books[:5]
            if len(valid_books) >= 2:
                final_groups.append({"title": title, "books": valid_books})
                used.update(valid_books)

        # 6. Fallback cho những sách còn dư
        remain = [n for n in product_ids if n not in used]
        if remain:
            final_groups.append({"title": "Có thể bạn cũng thích", "books": remain[:5]})

        return final_groups[:4]  # Giới hạn số nhóm trả về để LLM xử lý nhanh hơn
