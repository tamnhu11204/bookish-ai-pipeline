# semantic_search.py
import os
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"
)
COLLECTION_NAME = "product_vectors"

# Load model & Chroma
model = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)


def hybrid_search(query: str, top_k: int = 10, alpha: float = 0.75):
    if not query.strip():
        return []

    # 1. Semantic + Keyword search
    query_emb = model.encode(query, normalize_embeddings=True).tolist()

    semantic_results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k * 5,  # Lấy nhiều hơn để tổng hợp
        include=["metadatas", "distances"],
    )

    keyword_results = collection.query(
        query_texts=[query], n_results=top_k * 5, include=["metadatas", "distances"]
    )

    # 2. Tổng hợp điểm theo source_id
    product_scores = {}

    def add_scores(results, is_semantic=True):
        ids = results["ids"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        for i, chunk_id in enumerate(ids):
            meta = metadatas[i]
            source_id = meta.get("source_id")
            if not source_id:
                continue

            # Chuyển distance → score (càng gần 0 càng tốt)
            # Với cosine similarity: distance ~ 0 → giống, 1 → khác
            score = 1.0 / (1.0 + distances[i])  # chuyển thành score dương

            if is_semantic:
                score *= alpha
            else:
                score *= 1 - alpha

            product_scores[source_id] = product_scores.get(source_id, 0) + score

    add_scores(semantic_results, is_semantic=True)
    add_scores(keyword_results, is_semantic=False)

    # 3. Sắp xếp & trả về top_k sản phẩm
    ranked_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
    final_product_ids = [pid for pid, score in ranked_products[:top_k]]

    return final_product_ids
