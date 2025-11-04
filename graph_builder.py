import os
import pymongo
import networkx as nx
import pickle
import chromadb
from itertools import combinations
from bson.objectid import ObjectId
from dotenv import load_dotenv

# ==========================
# 1. CẤU HÌNH
# ==========================
load_dotenv()
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://tamnhu11204:nhunguyen11204@cluster0.kezkc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./ai_service/chroma_db")
GRAPH_OUTPUT_FILE = "book_graph.gpickle"
SIMILARITY_TOP_K = 5  # Số lượng sách tương đồng ngữ nghĩa cần tìm cho mỗi sách

# ==========================
# 2. KẾT NỐI
# ==========================
# Kết nối MongoDB
try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    products_collection = db["products"]
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit()

# Kết nối ChromaDB
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    products_chroma_collection = chroma_client.get_collection(name="product_vectors")
    print(
        f"Connected to ChromaDB at {CHROMA_PATH} and got collection 'product_vectors'."
    )
except Exception as e:
    print(f"Error connecting to ChromaDB or getting collection: {e}")
    exit()

# ==========================
# 3. XÂY DỰNG GRAPH
# ==========================


def build_book_graph():
    """
    Xây dựng một graph quan hệ sách bao gồm cả các mối quan hệ rõ ràng (metadata)
    và các mối quan hệ tương đồng ngữ nghĩa (vector similarity).
    """
    print("\nStarting graph construction...")
    G = nx.Graph()

    # --- Bước 1: Lấy toàn bộ dữ liệu sách từ MongoDB và xử lý ---
    print("Fetching all product data from MongoDB...")
    all_books = list(products_collection.find({"isDeleted": {"$ne": True}}))
    if not all_books:
        print("No books found in MongoDB. Exiting.")
        return

    # Tạo các map để nhóm sách -> Tối ưu hóa hiệu năng
    author_map = {}
    category_map = {}

    print("Processing book data and adding nodes to the graph...")
    for book in all_books:
        book_id = str(book["_id"])
        # Thêm node cho mỗi cuốn sách
        G.add_node(
            book_id,
            name=book.get("name", "N/A"),
            author=str(book.get("author")),
            category=str(book.get("category")),
        )

        # Nhóm sách theo tác giả
        author_id = str(book.get("author"))
        if author_id:
            if author_id not in author_map:
                author_map[author_id] = []
            author_map[author_id].append(book_id)

        # Nhóm sách theo thể loại
        category_id = str(book.get("category"))
        if category_id:
            if category_id not in category_map:
                category_map[category_id] = []
            category_map[category_id].append(book_id)

    print(f"Added {G.number_of_nodes()} book nodes.")

    print("Adding edges based on explicit relationships (author, category)...")

    # Cạnh "cùng tác giả"
    for author_id, book_ids in author_map.items():
        # Tạo tất cả các cặp sách có thể có trong danh sách
        for book1, book2 in combinations(book_ids, 2):
            G.add_edge(book1, book2, relationship="same_author")

    # Cạnh "cùng thể loại"
    for category_id, book_ids in category_map.items():
        for book1, book2 in combinations(book_ids, 2):
            if not G.has_edge(book1, book2):  # Chỉ thêm nếu chưa có cạnh nào
                G.add_edge(book1, book2, relationship="same_category")

    print(
        f"Added edges for explicit relationships. Total edges now: {G.number_of_edges()}"
    )

    print(
        f"Adding edges based on semantic similarity from ChromaDB (top {SIMILARITY_TOP_K})..."
    )

    # Lấy tất cả các ID đã được vector hóa từ Chroma
    chroma_ids = products_chroma_collection.get(include=[])["ids"]

    for book_id in chroma_ids:
        # Bỏ qua nếu sách không có trong graph (có thể đã bị xóa)
        if book_id not in G:
            continue

        # Truy vấn ChromaDB để tìm K sách tương đồng nhất
        # Chúng ta cần query K+1 vì kết quả đầu tiên sẽ là chính nó
        try:
            results = products_chroma_collection.query(
                query_texts=[
                    G.nodes[book_id]["name"]
                ],  # Có thể query bằng text hoặc vector
                n_results=SIMILARITY_TOP_K + 1,
                # where={"mongo_id": {"$ne": book_id}} # Có thể lọc để không trả về chính nó
            )

            # Lấy ra danh sách các id và khoảng cách/điểm tương đồng
            similar_ids = results["ids"][0]
            distances = results["distances"][0]

            for i in range(len(similar_ids)):
                similar_id = similar_ids[i]

                # Bỏ qua chính nó và các sách không có trong graph
                if similar_id == book_id or similar_id not in G:
                    continue

                # Thêm cạnh tương đồng, với trọng số là điểm tương đồng
                # ChromaDB trả về 'distance', similarity = 1 - distance
                similarity_score = 1 - distances[i]
                if similarity_score > 0:  # Chỉ thêm nếu có độ tương đồng
                    # Thêm cạnh nếu chưa tồn tại, hoặc cập nhật nếu cạnh mới tốt hơn
                    if not G.has_edge(book_id, similar_id):
                        G.add_edge(
                            book_id,
                            similar_id,
                            relationship="semantically_similar",
                            weight=round(similarity_score, 4),
                        )
        except Exception as e:
            print(f"Could not query similarity for book {book_id}: {e}")

    print(
        f"Graph construction complete. Total nodes: {G.number_of_nodes()}, Total edges: {G.number_of_edges()}"
    )

    # --- Bước 4: Lưu graph ---
    print(f"Saving graph to '{GRAPH_OUTPUT_FILE}'...")
    with open(GRAPH_OUTPUT_FILE, "wb") as f:
        pickle.dump(G, f)
    print("Graph saved successfully.")

    return G


# ==========================
# 5. MAIN
# ==========================
if __name__ == "__main__":
    book_graph = build_book_graph()
    mongo_client.close()
    print("\nMongoDB connection closed.")
    print("Process completed successfully!")
