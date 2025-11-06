import os
import sys
import networkx as nx
import pickle
from itertools import combinations
from dotenv import load_dotenv

# ==========================
# 0. THIẾT LẬP PATH ĐỂ IMPORT
# ==========================
# Thêm thư mục gốc (ai_service) vào Python Path để có thể import từ `app`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==========================
# 1. IMPORT CÁC THÀNH PHẦN ĐÃ MODULE HÓA
# ==========================
from app.connect_db.mongo_client import products_collection
from app.connect_db.vector_db import products_chroma_collection

# Tải các biến môi trường từ file .env
load_dotenv()

# ==========================
# 2. CẤU HÌNH SCRIPT
# ==========================
# Lấy đường dẫn file output từ .env, có giá trị mặc định
GRAPH_OUTPUT_FILE = os.getenv("GRAPH_OUTPUT_FILE", "./data/book_graph.gpickle")
SIMILARITY_TOP_K = 5  # Số lượng sách tương đồng ngữ nghĩa cần tìm cho mỗi sách


# ==========================
# 3. LOGIC XÂY DỰNG GRAPH
# ==========================
def build_book_graph():
    """
    Xây dựng một graph quan hệ sách bao gồm cả các mối quan hệ rõ ràng (metadata)
    và các mối quan hệ tương đồng ngữ nghĩa (vector similarity).
    """
    print("\nBắt đầu xây dựng graph quan hệ sách...")
    G = nx.Graph()

    # --- Bước 1: Lấy toàn bộ dữ liệu sách từ MongoDB (sử dụng collection đã import) ---
    print("Đang lấy dữ liệu sách từ MongoDB...")
    all_books = list(products_collection.find({"isDeleted": {"$ne": True}}))
    if not all_books:
        print("Không tìm thấy sách nào trong MongoDB. Kết thúc.")
        return

    author_map = {}
    category_map = {}

    print("Đang xử lý dữ liệu và thêm các node sách vào graph...")
    for book in all_books:
        book_id = str(book["_id"])
        G.add_node(
            book_id,
            name=book.get("name", "N/A"),
            author=str(book.get("author")),
            category=str(book.get("category")),
        )
        author_id = str(book.get("author"))
        if author_id:
            author_map.setdefault(author_id, []).append(book_id)

        category_id = str(book.get("category"))
        if category_id:
            category_map.setdefault(category_id, []).append(book_id)

    print(f"Đã thêm {G.number_of_nodes()} node sách.")

    # --- Bước 2: Thêm các cạnh dựa trên quan hệ rõ ràng (cùng tác giả, thể loại) ---
    print("Đang thêm các cạnh quan hệ rõ ràng (cùng tác giả, cùng thể loại)...")
    for author_id, book_ids in author_map.items():
        for book1, book2 in combinations(book_ids, 2):
            G.add_edge(book1, book2, relationship="same_author")

    for category_id, book_ids in category_map.items():
        for book1, book2 in combinations(book_ids, 2):
            if not G.has_edge(book1, book2):
                G.add_edge(book1, book2, relationship="same_category")

    print(f"Số cạnh hiện tại sau khi thêm quan hệ rõ ràng: {G.number_of_edges()}")

    # --- Bước 3: Thêm các cạnh dựa trên tương đồng ngữ nghĩa từ ChromaDB ---
    print(
        f"Đang thêm các cạnh tương đồng ngữ nghĩa từ ChromaDB (top {SIMILARITY_TOP_K})..."
    )

    # Lấy ID của tất cả các chunk từ ChromaDB
    chroma_results = products_chroma_collection.get(include=["metadatas"])

    # Gom các chunk lại theo source_id (product_id)
    product_chunks = {}
    for i, chunk_id in enumerate(chroma_results["ids"]):
        source_id = chroma_results["metadatas"][i].get("source_id")
        if source_id:
            product_chunks.setdefault(source_id, []).append(chunk_id)

    # Truy vấn sách tương đồng cho mỗi cuốn sách
    product_ids_in_graph = list(G.nodes)
    for i, book_id in enumerate(product_ids_in_graph):
        if book_id not in product_chunks:
            continue

        try:
            # Query bằng embedding của chunk đầu tiên của sách đó
            query_embedding = products_chroma_collection.get(
                ids=product_chunks[book_id][0], include=["embeddings"]
            )["embeddings"][0]

            results = products_chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=SIMILARITY_TOP_K + 5,  # Lấy nhiều hơn để lọc
            )

            # Xử lý kết quả trả về
            similar_product_ids = set()
            for j, distance in enumerate(results["distances"][0]):
                meta = results["metadatas"][0][j]
                similar_id = meta.get("source_id")

                if similar_id and similar_id != book_id and similar_id in G:
                    similar_product_ids.add((similar_id, distance))

            # Thêm cạnh cho K sách gần nhất
            sorted_similar = sorted(list(similar_product_ids), key=lambda x: x[1])
            for similar_id, distance in sorted_similar[:SIMILARITY_TOP_K]:
                similarity_score = 1 - distance
                if similarity_score > 0 and not G.has_edge(book_id, similar_id):
                    G.add_edge(
                        book_id,
                        similar_id,
                        relationship="semantically_similar",
                        weight=round(similarity_score, 4),
                    )
        except Exception as e:
            print(f"[LỖI] Không thể truy vấn sách tương đồng cho {book_id}: {e}")

        if (i + 1) % 100 == 0:
            print(f"  Đã xử lý {i + 1}/{len(product_ids_in_graph)} sách...")

    print(
        f"Xây dựng graph hoàn tất. Tổng số node: {G.number_of_nodes()}, Tổng số cạnh: {G.number_of_edges()}"
    )

    # --- Bước 4: Lưu graph vào file ---
    print(f"Đang lưu graph vào file: '{GRAPH_OUTPUT_FILE}'...")
    # Tự động tạo thư mục chứa file nếu chưa tồn tại
    output_dir = os.path.dirname(GRAPH_OUTPUT_FILE)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(GRAPH_OUTPUT_FILE, "wb") as f:
        pickle.dump(G, f)
    print("✅ Đã lưu graph thành công.")

    return G


# ==========================
# 4. ĐIỂM BẮT ĐẦU CHẠY SCRIPT
# ==========================
if __name__ == "__main__":
    build_book_graph()
    print("\n🎉 Xây dựng graph hoàn tất!")
