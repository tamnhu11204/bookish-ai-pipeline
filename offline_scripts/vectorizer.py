# offline_scripts/product_vectorizer.py
import os
import sys
import re
import unicodedata
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from typing import List

# Thêm thư mục gốc vào Python Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import DB
from app.connect_db.mongo_client import products, categories
from app.connect_db.vector_db import (
    search_vectors,  # ← Collection cho Semantic Search (có chunking)
    recommend_vectors,  # ← Collection cho Dynamic Menu (1 vector/sách)
    get_model,
)

# Load env + model
load_dotenv()
MODEL_NAME = os.getenv("EMBEDDING_MODEL")
sbert_model = get_model()

print(f"Model đã tải: {MODEL_NAME}")


# ==========================
# 1. CHUNKING CHO SEARCH (CHI TIẾT)
# ==========================
def chunk_text_semantic(
    text: str, max_words: int = 200, overlap_words: int = 50
) -> List[str]:
    """
    Chia mô tả sách thành nhiều chunk nhỏ (theo từ), giữ ngữ nghĩa, có overlap.
    Dùng cho Semantic Search → tìm chính xác từng đoạn.
    """
    if not text or not isinstance(text, str):
        return []

    # Chuẩn hóa Unicode
    text = unicodedata.normalize("NFC", text).strip()
    if not text:
        return []

    # Tách câu
    sentence_endings = r"[.!?]\s+|[.!?]$|\n+"
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        # Nếu vượt giới hạn → đóng chunk
        if current_word_count + sentence_words > max_words and current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)

            # Tạo overlap: lấy N từ cuối chunk cũ
            overlap_text = (
                " ".join(current_chunk[-overlap_words:])
                if len(current_chunk) > overlap_words
                else " ".join(current_chunk)
            )
            current_chunk = overlap_text.split()
            current_word_count = len(current_chunk)
        else:
            current_chunk.extend(sentence.split())
            current_word_count += sentence_words

    # Thêm chunk cuối
    if current_chunk:
        final_chunk = " ".join(current_chunk).strip()
        if final_chunk:
            chunks.append(final_chunk)

    return [c for c in chunks if len(c.split()) > 20]  # loại chunk quá ngắn


# ==========================
# 2. TẠO TEXT CHO RECOMMEND (TỔNG HỢP)
# ==========================
def build_recommend_text(
    name: str, author: str, category: str, description: str
) -> str:
    """
    Tạo 1 đoạn văn ngắn gọn cho 1 vector / sách.
    Dùng cho Dynamic Menu → gợi ý tổng thể.
    """
    desc_sentences = re.split(r"[.!?]\s+", description)
    short_desc = ". ".join(desc_sentences[:3]).strip()
    if len(desc_sentences) > 3:
        short_desc += "."

    return f"""
    Tên sách: {name}
    Tác giả: {author}
    Thể loại: {category}
    Mô tả: {short_desc}
    """.strip()


# ==========================
# 3. XỬ LÝ SẢN PHẨM → 2 COLLECTION
# ==========================
def process_products():
    print("\nBắt đầu vector hóa sản phẩm...")

    # Cache category & author
    categories_map = {
        str(c["_id"]): c.get("name", "") for c in categories.find({}, {"name": 1})
    }
    all_products = list(products.find({"isDeleted": {"$ne": True}}))
    print(f"Tìm thấy {len(all_products)} sản phẩm.")

    # Dữ liệu cho 2 collection
    search_docs, search_ids, search_meta = [], [], []
    recommend_docs, recommend_ids, recommend_meta = [], [], []

    for idx, product in enumerate(all_products):
        pid = str(product["_id"])
        name = product.get("name", "").strip()
        description = product.get("description", "").strip()
        category_name = categories_map.get(str(product.get("category")), "")
        author = str(product.get("author", ""))

        # === 1. RECOMMEND: 1 vector / sách ===
        recommend_text = build_recommend_text(name, author, category_name, description)
        if recommend_text and len(recommend_text) > 20:
            recommend_docs.append(recommend_text)
            recommend_ids.append(pid)
            recommend_meta.append(
                {
                    "source_id": pid,
                    "name": name,
                    "author": author,
                    "category": category_name,
                    "type": "product",
                }
            )

        # === 2. SEARCH: nhiều chunk từ description ===
        if description:
            chunks = chunk_text_semantic(description)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{pid}_chunk_{i}"
                search_docs.append(chunk)
                search_ids.append(chunk_id)
                search_meta.append(
                    {
                        "source_id": pid,
                        "chunk_index": i,
                        "name": name,
                        "author": author,
                        "category": category_name,
                        "type": "product_chunk",
                    }
                )

        if (idx + 1) % 100 == 0:
            print(f"Đã xử lý {idx + 1}/{len(all_products)} sản phẩm...")

    # === THÊM VÀO CHROMA ===
    def add_to_collection(collection, docs, ids, metas, name):
        if not docs:
            print(f"Không có dữ liệu cho {name}")
            return
        print(f"Đang tạo embedding cho {len(docs)} {name}...")
        embeddings = sbert_model.encode(docs, normalize_embeddings=True).tolist()

        batch_size = 5000
        for i in range(0, len(docs), batch_size):
            batch_emb = embeddings[i : i + batch_size]
            batch_docs = docs[i : i + batch_size]
            batch_meta = metas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            collection.add(
                embeddings=batch_emb,
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
            )
            print(f"  → Batch {i//batch_size + 1}: {len(batch_docs)} records")

        print(f"Hoàn tất thêm {len(docs)} vào {name}")

    # Thêm vào từng collection
    add_to_collection(
        recommend_vectors,
        recommend_docs,
        recommend_ids,
        recommend_meta,
        "recommend_vectors",
    )
    add_to_collection(
        search_vectors, search_docs, search_ids, search_meta, "search_vectors"
    )

    print("\nVector hóa sản phẩm HOÀN TẤT!")


# ==========================
# 4. CHẠY SCRIPT
# ==========================
if __name__ == "__main__":
    process_products()
