import os
import sys
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv
import unicodedata
from chromadb.utils import embedding_functions
import re
from typing import List

# Thêm thư mục gốc (ai_service) vào Python Path để có thể import từ `app`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==========================
# 1. IMPORT CÁC THÀNH PHẦN ĐÃ MODULE HÓA
# ==========================
# Import trực tiếp các collection đã được khởi tạo từ module db
from app.connect_db.mongo_client import products, categories
from app.connect_db.vector_db import product_vectors as product_chroma_collection

# Tải các biến môi trường
load_dotenv()

# ==========================
# 2. CẤU HÌNH MODEL
# ==========================
MODEL_NAME = os.getenv("EMBEDDING_MODEL")
CHROMA_PATH = os.getenv("CHROMA_PATH")
PRODUCT_COLLECTION_NAME = os.getenv("PRODUCT_COLLECTION_NAME", "product_vectors")

# *** THÊM MỚI: TẠO EMBEDDING FUNCTION ***
# Đây là cách để "bảo" ChromaDB biết chúng ta đang dùng model nào
sbert_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=MODEL_NAME
)

# Tải model (vẫn cần thiết vì chúng ta tự tính embedding)
print(f"Đang tải model embedding: {MODEL_NAME}...")
sbert_model = SentenceTransformer(MODEL_NAME)
print("Model đã tải xong.")


# ==========================
# 3. CÁC HÀM HỖ TRỢ (CHUNKING)
# ==========================
def chunk_text_semantic(
    text: str,
    max_tokens: int = 250,
    overlap_tokens: int = 50,
    model_name: str = "bkai-foundation-models/vietnamese-bi-encoder",
) -> List[str]:
    """
    Chia văn bản theo câu, giữ ngữ nghĩa, không cắt ngang câu.
    """
    if not text or not isinstance(text, str):
        return []

    # Chuẩn hóa Unicode
    text = unicodedata.normalize("NFC", text).strip()
    if not text:
        return []

    # Tách câu tiếng Việt (dùng regex thông minh)
    # Xử lý: dấu chấm, chấm than, hỏi, xuống dòng, v.v.
    sentence_endings = r"[.!?]\s+|[.!?]$|\n+"
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Load tokenizer của model để đếm token chính xác
    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_name)
    except:
        print("Warning: Không load được tokenizer, dùng word count thay thế")
        tokenizer = None

    def count_tokens(text):
        if tokenizer:
            return len(tokenizer.encode(text, add_special_tokens=False))
        else:
            return len(text.split())  # fallback

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence + ".")  # + dấu chấm để sát thực tế

        # Nếu thêm câu này vượt quá giới hạn
        if current_tokens + sentence_tokens > max_tokens and current_chunk:
            # Đóng chunk hiện tại
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)

            # Tính overlap: lấy N câu cuối của chunk cũ làm đầu chunk mới
            overlap_text = ""
            overlap_count = 0
            for prev_sent in reversed(current_chunk):
                if overlap_count + count_tokens(prev_sent) <= overlap_tokens:
                    overlap_text = prev_sent + " " + overlap_text
                    overlap_count += count_tokens(prev_sent)
                else:
                    break

            # Bắt đầu chunk mới với overlap
            current_chunk = [overlap_text.strip()] if overlap_text.strip() else []
            current_tokens = count_tokens(overlap_text)

        # Thêm câu vào chunk
        current_chunk.append(sentence)
        current_tokens += sentence_tokens

    # Thêm chunk cuối
    if current_chunk:
        final_chunk = " ".join(current_chunk).strip()
        if final_chunk:
            chunks.append(final_chunk)

    return chunks


def get_embeddings(texts):
    # Sử dụng normalize_embeddings=True để chuẩn hóa vector, giúp tính toán cosine similarity hiệu quả
    return sbert_model.encode(texts, normalize_embeddings=True).tolist()


# ==========================
# 4. LOGIC XỬ LÝ SẢN PHẨM
# ==========================
def process_products():
    print("\nBắt đầu xử lý và vector hóa sản phẩm...")

    # Load danh mục từ collection đã import
    categories_map = {
        str(cat["_id"]): cat.get("name", "") for cat in categories.find({}, {"name": 1})
    }

    # Lấy sản phẩm từ collection đã import
    all_products = list(products.find({"isDeleted": {"$ne": True}}))
    print(f"Tìm thấy {len(all_products)} sản phẩm để xử lý.")

    documents, ids, metadatas = [], [], []

    for idx, product in enumerate(all_products):
        name = product.get("name", "").strip()
        description = product.get("description", "").strip()
        category_id = str(product.get("category"))
        category_name = categories_map.get(category_id, "")

        full_text = f"{name}. Thể loại: {category_name}. {description}".strip()
        if not full_text:
            continue

        chunks = chunk_text_semantic(
            text=full_text, max_tokens=250, overlap_tokens=50, model_name=MODEL_NAME
        )

        for chunk_idx, chunk in enumerate(chunks):
            chunk_id = f"{product['_id']}_chunk_{chunk_idx}"
            documents.append(chunk)
            ids.append(chunk_id)
            metadatas.append(
                {
                    "source_id": str(product["_id"]),
                    "name": name,
                    "category": category_name,
                    "chunk_index": chunk_idx,
                    "type": "product",
                }
            )

        if (idx + 1) % 100 == 0:
            print(f"Đã xử lý {idx + 1}/{len(all_products)} sản phẩm...")

    if not documents:
        print("Không có tài liệu nào để thêm vào ChromaDB.")
        return

    print(f"Chuẩn bị thêm {len(documents)} chunks vào ChromaDB...")
    # Thêm vào Chroma theo batch
    batch_size = 1000
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]

        print(f"Đang tạo embedding cho batch {i//batch_size + 1}...")
        batch_emb = get_embeddings(batch_docs)

        print(f"Đang thêm batch {i//batch_size + 1} vào ChromaDB...")
        product_chroma_collection.add(
            embeddings=batch_emb,
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids,
        )

    print(
        f"Hoàn tất! Đã thêm {len(documents)} chunk vào ChromaDB tại đường dẫn: '{CHROMA_PATH}'"
    )


# ==========================
# 5. ĐIỂM BẮT ĐẦU CHẠY SCRIPT
# ==========================
if __name__ == "__main__":
    process_products()
    print("\nVector hóa hoàn tất!")
