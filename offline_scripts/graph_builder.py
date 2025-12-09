import os
import sys
import networkx as nx
import pickle
from itertools import combinations
from bson import ObjectId
from dotenv import load_dotenv

# Thêm đường dẫn gốc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connect_db.mongo_client import (
    products,
    categories,
    authors,
)  # THÊM authors nếu có, không thì bỏ
from app.connect_db.vector_db import recommend_vectors

load_dotenv()

GRAPH_OUTPUT_FILE = os.getenv("GRAPH_OUTPUT_FILE", "./data/book_graph.gpickle")
SIMILARITY_TOP_K = 6  # tăng lên 6 cho chắc


def resolve_name(ref, collection, field_name="name"):
    """Chuyển ObjectId hoặc dict thành tên thật"""
    if not ref:
        return "Không rõ"
    if isinstance(ref, dict):
        return ref.get(field_name, "Không rõ")
    if isinstance(ref, str) and len(ref) == 24:  # ObjectId hex
        try:
            doc = collection.find_one({"_id": ObjectId(ref)}, {field_name: 1})
            return doc.get(field_name, "Không rõ") if doc else "Không rõ"
        except:
            return "Không rõ"
    return str(ref)


def build_book_graph():
    print("\nBẮT ĐẦU XÂY DỰNG GRAPH SÁCH – PHIÊN BẢN ĐỈNH CAO 2025")
    G = nx.Graph()

    print("Đang tải dữ liệu sách từ MongoDB...")
    all_books = list(products.find({"isDeleted": {"$ne": True}}))
    if not all_books:
        print("Không có sách nào!")
        return

    print(f"Đang xử lý {len(all_books)} cuốn sách – thêm node + lấy tên thật...")
    for book in all_books:
        book_id = str(book["_id"])

        # LẤY TÊN THẬT CỦA TÁC GIẢ & THỂ LOẠI
        author_name = resolve_name(book.get("author"), products, "authorName")
        if author_name == "Không rõ":
            author_name = book.get("authorName", "Không rõ tác giả")

        category_name = resolve_name(book.get("category"), categories, "name")
        if category_name == "Không rõ":
            category_name = book.get("categoryName", "Không rõ thể loại")

        G.add_node(
            book_id,
            name=book.get("name", "Không tên"),
            author=author_name,
            category=category_name,
        )

    print(f"Đã thêm {G.number_of_nodes()} node với tên tác giả/thể loại chuẩn!")

    # === THÊM CẠNH: CÙNG TÁC GIẢ ===
    print("Thêm cạnh: cùng tác giả...")
    author_groups = {}
    for node, data in G.nodes(data=True):
        author = data["author"]
        author_groups.setdefault(author, []).append(node)

    for author, books in author_groups.items():
        if len(books) >= 2:
            for b1, b2 in combinations(books, 2):
                G.add_edge(b1, b2, relationship="same_author", weight=1.0)

    # === THÊM CẠNH: CÙNG THỂ LOẠI ===
    print("Thêm cạnh: cùng thể loại...")
    category_groups = {}
    for node, data in G.nodes(data=True):
        cat = data["category"]
        category_groups.setdefault(cat, []).append(node)

    for cat, books in category_groups.items():
        if len(books) >= 2:
            for b1, b2 in combinations(books, 2):
                if not G.has_edge(b1, b2):
                    G.add_edge(b1, b2, relationship="same_category", weight=0.8)

    # === THÊM CẠNH: TƯƠNG ĐỒNG NGỮ NGHĨA ===
    print(f"Thêm cạnh ngữ nghĩa (top {SIMILARITY_TOP_K})...")
    chroma_results = recommend_vectors.get(include=["metadatas"])
    product_chunks = {}
    for i, chunk_id in enumerate(chroma_results["ids"]):
        source_id = chroma_results["metadatas"][i].get("source_id")
        if source_id:
            product_chunks.setdefault(source_id, []).append(chunk_id)

    count = 0
    for book_id in G.nodes:
        if book_id not in product_chunks:
            continue
        try:
            emb = recommend_vectors.get(
                ids=[product_chunks[book_id][0]], include=["embeddings"]
            )["embeddings"][0]
            results = recommend_vectors.query(
                query_embeddings=[emb],
                n_results=SIMILARITY_TOP_K + 10,
                include=["metadatas", "distances"],
            )
            for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
                sid = meta.get("source_id")
                if sid and sid != book_id and sid in G and dist < 0.5:  # ngưỡng tốt
                    score = round(1 - dist, 4)
                    if not G.has_edge(book_id, sid):
                        G.add_edge(
                            book_id,
                            sid,
                            relationship="semantically_similar",
                            weight=score,
                        )
        except Exception as e:
            continue

        count += 1
        if count % 200 == 0:
            print(f"  Đã xử lý {count}/{len(G.nodes)} sách ngữ nghĩa...")

    print(f"HOÀN TẤT! Graph có {G.number_of_nodes()} node, {G.number_of_edges()} cạnh")

    # Lưu file
    os.makedirs(os.path.dirname(GRAPH_OUTPUT_FILE), exist_ok=True)
    with open(GRAPH_OUTPUT_FILE, "wb") as f:
        pickle.dump(G, f)
    print(f"ĐÃ LƯU GRAPH TẠI: {GRAPH_OUTPUT_FILE}")

    return G


if __name__ == "__main__":
    build_book_graph()
    print("XONG! Giờ chạy master chain sẽ thấy combo đẹp như mơ!")
