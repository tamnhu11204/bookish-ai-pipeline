"""
recommender_core.py

Logic:
 - Lấy lịch sử user từ data_access.get_user_interactions(user_id)
 - Với mỗi product_id: lấy document product từ MongoDB và tạo text (name + category + description)
 - Encode text bằng cùng SentenceTransformer model (dùng EMBEDDING_MODEL từ .env)
 - Tính mean vector của history -> query ChromaDB
 - Gom nhóm theo author/category đơn giản
"""

import os
import numpy as np
from chromadb import PersistentClient
from dotenv import load_dotenv
import networkx as nx
from bson import ObjectId

# load env
load_dotenv()

# model name (phải trùng với create_vectors.py)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bkai-foundation-models/vietnamese-bi-encoder")
CHROMA_PATH = os.getenv("CHROMA_PATH", "../chroma_db")  # adjust if needed
PRODUCT_COLLECTION_NAME = os.getenv("PRODUCT_COLLECTION_NAME", "product_vectors")

# ------------------------
# load model SentenceTransformer (same as used to create vectors)
# ------------------------
try:
    from sentence_transformers import SentenceTransformer
    print(f"🔹 Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    # encode with normalize_embeddings=True if create_vectors used normalize_embeddings
    MODEL_NORMALIZE = True
    print("✅ Model loaded")
except Exception as e:
    print("❌ Cannot load sentence-transformers model:", e)
    model = None
    MODEL_NORMALIZE = False

# ------------------------
# connect chroma
# ------------------------
try:
    print(f"🔹 Connecting to ChromaDB at: {CHROMA_PATH}")
    chroma_client = PersistentClient(path=CHROMA_PATH)
    products_collection = chroma_client.get_or_create_collection(name=PRODUCT_COLLECTION_NAME)
    print(f"✅ Connected to Chroma collection '{PRODUCT_COLLECTION_NAME}'")
except Exception as e:
    print("❌ Cannot connect to ChromaDB:", e)
    chroma_client = None
    products_collection = None

# ------------------------
# connect mongodb (products) - using same DB as data_access or new connection
# ------------------------
try:
    # try import db from data_access if available
    from data_access import db
    products_col = db["products"]
    print("✅ Reusing MongoDB connection from data_access")
except Exception:
    from pymongo import MongoClient
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    products_col = db["products"]
    print("✅ Connected to MongoDB (new client)")

# import get_user_interactions
from data_access import get_user_interactions

# ------------------------
# helper: build representation text for a product doc (same logic as create_vectors)
# ------------------------
def build_product_text(product_doc):
    if not product_doc:
        return ""
    name = (product_doc.get("name") or "").strip()
    description = (product_doc.get("description") or "").strip()
    # try to get category name if it's an ObjectId or string; if it's id, we can't resolve here simply
    category = product_doc.get("category")
    if isinstance(category, dict):
        category_name = category.get("name", "")
    else:
        category_name = str(category) if category else ""
    combined = f"{name}. Thể loại: {category_name}. {description}".strip()
    return combined

# ------------------------
# helper: compute embedding for a product (from mongo doc)
# ------------------------
def compute_embedding_for_product(product_id):
    """
    product_id: string (ObjectId as string)
    Returns: np.array vector or None
    """
    try:
        # fetch product from MongoDB
        try:
            obj_id = ObjectId(product_id)
        except Exception:
            obj_id = product_id
        doc = products_col.find_one({"_id": obj_id})
        if not doc:
            # try searching by string id in source_id metadata (fallback)
            return None

        text = build_product_text(doc)
        if not text:
            return None
        # use model to encode
        if not model:
            return None
        emb = model.encode([text], normalize_embeddings=MODEL_NORMALIZE)[0]
        return np.array(emb, dtype=float)
    except Exception as e:
        print(f"[WARN] compute_embedding_for_product({product_id}) failed: {e}")
        return None

# ------------------------
# main function
# ------------------------
def generate_behavior_recommendations(user_id: str, k: int = 20):
    if not products_collection:
        return {"error": "ChromaDB collection not available"}

    # 1) get user history
    user_data = get_user_interactions(user_id)
    # summary expected
    summary = user_data.get("summary", {}) if isinstance(user_data, dict) else {}
    product_ids = list(set(
        (summary.get("viewed", []) or []) +
        (summary.get("cart", []) or []) +
        (summary.get("favorite", []) or []) +
        (summary.get("purchased", []) or [])
    ))

    if not product_ids:
        return {"user_id": user_id, "note": "no_history", "recommended": [], "groups": []}

    # 2) compute embeddings for each product in history (fallback: find chunk embeddings if desired)
    embeddings = []
    valid_ids = []
    for pid in product_ids:
        emb = compute_embedding_for_product(pid)
        if emb is not None:
            embeddings.append(emb)
            valid_ids.append(pid)

    if not embeddings:
        return {"user_id": user_id, "note": "no_embeddings_found_for_history", "recommended": [], "groups": []}

    # 3) user vector mean
    user_vector = np.mean(np.stack(embeddings, axis=0), axis=0).tolist()

    # 4) query chroma
    try:
        res = products_collection.query(
    query_embeddings=[user_vector],
    n_results=k,
    include=["documents", "metadatas", "distances"]
)

    except Exception as e:
        return {"error": f"Chroma query failed: {e}"}

    rec_ids = res.get("ids", [[]])[0]
    rec_distances = res.get("distances", [[]])[0] if res.get("distances") else []
    rec_metadatas = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
    rec_documents = res.get("documents", [[]])[0] if res.get("documents") else []

    # 5) fetch product docs for returned ids if metadata has source_id else map using metadata
    # note: create_vectors used chunk ids like "{product_id}_chunk_i" and metadata.source_id contains product_id
    # we will try to map result chunk ids back to source_id (product id) if available in metadata
    results = []
    for idx, cid in enumerate(rec_ids):
        meta = rec_metadatas[idx] if idx < len(rec_metadatas) else {}
        # if metadata includes source_id, provide that
        source_id = meta.get("source_id") or meta.get("mongo_id") or None
        results.append({
            "id": cid,
            "source_product_id": source_id,
            "distance": float(rec_distances[idx]) if idx < len(rec_distances) else None,
            "metadata": meta,
            "document": rec_documents[idx] if idx < len(rec_documents) else None
        })

    # 6) group results simply by source_product_id (or by metadata author if exists)
    # fetch product metadata from products_col for better grouping
    product_map = {}
    source_ids = [r["source_product_id"] for r in results if r["source_product_id"]]
    # unique and keep as ObjectId or string
    unique_src = list(dict.fromkeys(source_ids))
    for s in unique_src:
        try:
            obj = ObjectId(s)
        except Exception:
            obj = s
        pdoc = products_col.find_one({"_id": obj})
        if pdoc:
            product_map[s] = {
                "id": str(pdoc.get("_id")),
                "name": pdoc.get("name"),
                "author": str(pdoc.get("author")) if pdoc.get("author") else None,
                "category": str(pdoc.get("category")) if pdoc.get("category") else None,
                "img": pdoc.get("img")
            }

    # assemble recommended list
    recommended = []
    for r in results:
        recommended.append({
            "chunk_id": r["id"],
            "product_id": r["source_product_id"],
            "score": r["distance"],
            "metadata": r["metadata"],
            "document": r["document"],
            "product": product_map.get(r["source_product_id"])
        })

    # grouping by author as fallback
    groups = {}
    for it in recommended:
        prod = it.get("product")
        key = (prod.get("author") if prod else None) or "Khác"
        groups.setdefault(key, []).append(it)

    group_list = []
    for author, items in groups.items():
        group_list.append({"title": f"Sách cùng tác giả: {author}" if author != "Khác" else "Sách khác", "books": items[:5]})

    return {"user_id": user_id, "note": "success", "recommended": recommended, "groups": group_list}


# quick debug
if __name__ == "__main__":
    test_user = os.getenv("TEST_USER_ID", "6868164751471f57737434d5")
    out = generate_behavior_recommendations(test_user, k=10)
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))
