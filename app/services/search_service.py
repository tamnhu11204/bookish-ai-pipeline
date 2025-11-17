# app/services/search_service.py
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# ==========================
# 1. IMPORTS TỪ MODULE KẾT NỐI (THAY ĐỔI)
# ==========================
# Import collection đã được khởi tạo sẵn và đặt bí danh `collection`
# để không cần thay đổi code trong hàm `hybrid_search`
from app.connect_db.vector_db import search_vectors as collection

# Tải biến môi trường chỉ để lấy tên model
load_dotenv()
MODEL_NAME = os.getenv("EMBEDDING_MODEL")

# ==========================
# 2. TẢI MODEL (Chỉ một lần)
# ==========================
try:
    print(f"(Search) Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("(Search) Model loaded")
except Exception as e:
    model = None
    print(f"(Search) Cannot load sentence-transformers model: {e}")
    raise RuntimeError("Failed to load SentenceTransformer model") from e


# ==========================
# 3. HÀM TÌM KIẾM (LOGIC GIỮ NGUYÊN)
# ==========================
def hybrid_search(query: str, top_k: int = 10, alpha: float = 0.75):
    """
    Thực hiện tìm kiếm lai (hybrid search) kết hợp semantic và keyword.
    Sử dụng collection đã được import từ module `connect_db`.
    """
    if not query.strip() or not model:
        return []

    query_emb = model.encode(query, normalize_embeddings=True).tolist()

    # Query vector để tìm kiếm ngữ nghĩa
    semantic_results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k * 5,  # Lấy nhiều hơn để tổng hợp
        include=["metadatas", "distances"],
    )

    # Query text để tìm kiếm từ khóa
    keyword_results = collection.query(
        query_texts=[query], n_results=top_k * 5, include=["metadatas", "distances"]
    )

    product_scores = {}

    def add_scores(results, weight):
        # Kiểm tra dữ liệu trả về có hợp lệ không
        if not results or not results.get("ids") or not results["ids"][0]:
            return

        for i, meta in enumerate(results["metadatas"][0]):
            source_id = meta.get("source_id")
            if not source_id:
                continue

            # Chuyển distance thành score (càng gần 0 càng tốt)
            distance = results["distances"][0][i]
            score = 1.0 - distance  # Đối với cosine similarity đã chuẩn hóa

            product_scores[source_id] = product_scores.get(source_id, 0) + (
                score * weight
            )

    add_scores(semantic_results, alpha)
    add_scores(keyword_results, 1 - alpha)

    if not product_scores:
        return []

    ranked_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)

    # Trả về danh sách các product ID
    final_product_ids = [pid for pid, score in ranked_products[:top_k]]
    return final_product_ids
