# services/search_service.py
import os
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Khởi tạo mô hình và kết nối ChromaDB
try:
    print(f"🔹 Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_collection("product_vectors")
    print("✅ ChromaDB connected & model loaded successfully!")
except Exception as e:
    print(f"❌ Lỗi khởi tạo dịch vụ tìm kiếm: {e}")
    model = None
    collection = None


def semantic_search(query: str, top_k: int = 10):
    """Hàm thực hiện tìm kiếm ngữ nghĩa trong ChromaDB"""
    if not model or not collection:
        print("⚠️ Model hoặc Chroma collection chưa sẵn sàng.")
        return []

    try:
        query_emb = model.encode(query).tolist()
        results = collection.query(query_embeddings=[query_emb], n_results=top_k)
        ids = results.get("ids", [[]])[0]
        return ids
    except Exception as e:
        print(f"❌ Lỗi trong semantic_search: {e}")
        return []
