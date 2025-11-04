import chromadb
from sentence_transformers import SentenceTransformer

# 1. Load model & collection
model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("product_vectors")

# 2. Tạo vector truy vấn
query = "Sách lập trình Python nâng cao"
query_vector = model.encode([query], normalize_embeddings=True).tolist()[0]

# 3. Truy vấn
results = collection.query(
    query_embeddings=[query_vector],
    n_results=5,
)

# 4. In kết quả
for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"✅ {meta.get('name', 'Không tên')} | Thể loại: {meta.get('category', '')}")
    print(f"→ {doc[:200]}...\n")
