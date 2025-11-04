# create_vectors.py
import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from bson.objectid import ObjectId
from dotenv import load_dotenv
import re
import unicodedata

load_dotenv()

# ==========================
# 1. CẤU HÌNH
# ==========================
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"
)

# Tải model (có thể cần GPU hoặc dùng CPU chậm hơn)
print(f"Đang tải model embedding: {MODEL_NAME}")
sbert_model = SentenceTransformer(MODEL_NAME)

# Embedding function cho Chroma
sbert_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=MODEL_NAME
)


# ==========================
# 2. CHUNKING
# ==========================
def chunk_text(text: str, max_tokens: int = 250, overlap: int = 50):
    """
    Chia văn bản thành các chunk nhỏ, giữ ngữ nghĩa.
    250 token ~ 180-200 từ (tùy ngôn ngữ)
    """
    if not text or not isinstance(text, str):
        return []

    # Chuẩn hóa Unicode
    text = unicodedata.normalize("NFC", text)
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + max_tokens]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
        i += max_tokens - overlap
        if i >= len(words) and chunk_words:
            break
    return chunks


def get_embeddings(texts):
    return sbert_model.encode(texts, normalize_embeddings=True).tolist()


# ==========================
# 3. KẾT NỐI DB
# ==========================
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
products_collection = db["products"]
categories_collection = db["categories"]

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
product_collection = chroma_client.get_or_create_collection(
    name="product_vectors", embedding_function=sbert_ef
)


# ==========================
# 4. XỬ LÝ SẢN PHẨM VỚI CHUNKING
# ==========================
def process_products():
    print("\nBắt đầu xử lý sản phẩm với CHUNKING + MODEL MỚI...")

    # Load danh mục
    categories_map = {
        str(cat["_id"]): cat.get("name", "")
        for cat in categories_collection.find({}, {"name": 1})
    }

    all_products = list(products_collection.find({"isDeleted": {"$ne": True}}))
    print(f"Tìm thấy {len(all_products)} sản phẩm.")

    documents, ids, metadatas = [], [], []

    for idx, product in enumerate(all_products):
        name = product.get("name", "").strip()
        description = product.get("description", "").strip()
        category_id = str(product.get("category"))
        category_name = categories_map.get(category_id, "")

        # Tạo nội dung đầy đủ
        full_text = f"{name}. Thể loại: {category_name}. {description}".strip()
        if not full_text:
            continue

        # CHIA NHỎ THÀNH NHIỀU CHUNK
        chunks = chunk_text(full_text, max_tokens=250, overlap=30)

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
                    "source": "product",
                }
            )

        if (idx + 1) % 100 == 0:
            print(f"Đã xử lý {idx + 1}/{len(all_products)} sản phẩm...")

    # Thêm vào Chroma theo batch
    if documents:
        batch_size = 1000
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]
            batch_emb = get_embeddings(batch_docs)

            product_collection.add(
                embeddings=batch_emb,
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
            )
            print(
                f"Đã thêm batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}"
            )

    print(f"Hoàn tất! Đã thêm {len(documents)} chunk vào ChromaDB.")


# ==========================
# 5. MAIN
# ==========================
if __name__ == "__main__":
    process_products()
    mongo_client.close()
    print("Hoàn tất tạo vector với chunking + model mới!")
