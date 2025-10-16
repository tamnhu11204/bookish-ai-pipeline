import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

# ==========================
# 1. CẤU HÌNH
# ==========================
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

# Model embedding
sbert_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Embedding function cho ChromaDB
sbert_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def get_embeddings(texts):
    return sbert_model.encode(texts).tolist()

# ==========================
# 2. KẾT NỐI MONGODB
# ==========================
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    products_collection = db["products"]
    newstrend_collection = db["newstrend"]
    authors_collection = db["authors"]
    publishers_collection = db["publishers"]
    languages_collection = db["languages"]
    formats_collection = db["formats"]
    categories_collection = db["categories"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    exit()

# ==========================
# 3. KHỞI TẠO CHROMADB
# ==========================
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    print(f"✅ Connected to ChromaDB at {CHROMA_PATH} successfully!")
except Exception as e:
    print(f"❌ Error connecting to ChromaDB: {e}")
    exit()

products_chroma_collection = chroma_client.get_or_create_collection(
    name="product_vectors",
    embedding_function=sbert_ef
)
newstrend_chroma_collection = chroma_client.get_or_create_collection(
    name="newstrend_vectors",
    embedding_function=sbert_ef
)

# ==========================
# 4. XỬ LÝ DỮ LIỆU SẢN PHẨM
# ==========================
def process_products_data():
    print("\n🛍️ Processing products data...")
    documents_to_add, ids_to_add, metadatas_to_add = [], [], []

    all_products = products_collection.find({"isDeleted": {"$ne": True}})
    for product in all_products:
        name = product.get("name", "")
        description = product.get("description", "")
        price = product.get("price", 0)
        discount = product.get("discount", 0)
        publish_year = product.get("publishYear", "")
        dimensions = product.get("dimensions", "")
        weight = product.get("weight", "")
        page = product.get("page", "")

        # --- JOIN các bảng liên quan ---
        def get_name_by_id(collection, oid):
            if isinstance(oid, ObjectId):
                doc = collection.find_one({"_id": oid})
                if doc:
                    return doc.get("name", "")
            return ""

        author_name = get_name_by_id(authors_collection, product.get("author"))
        publisher_name = get_name_by_id(publishers_collection, product.get("publisher"))
        language_name = get_name_by_id(languages_collection, product.get("language"))
        format_name = get_name_by_id(formats_collection, product.get("format"))
        category_name = get_name_by_id(categories_collection, product.get("category"))

        # --- GHÉP THÀNH TEXT GIÀU NGỮ NGHĨA ---
        combined_text = (
            f"Tên sản phẩm: {name}. "
            f"Tác giả: {author_name}. "
            f"Thể loại: {category_name}. "
            f"Nhà xuất bản: {publisher_name}. "
            f"Ngôn ngữ: {language_name}. "
            f"Định dạng: {format_name}. "
            f"Năm xuất bản: {publish_year}. "
            f"Trọng lượng: {weight} gram. "
            f"Kích thước: {dimensions}. "
            f"Số trang: {page}. "
            f"Giá: {price} đồng. Giảm giá: {discount}%. "
            f"Mô tả: {description}"
        )

        documents_to_add.append(combined_text)
        ids_to_add.append(str(product["_id"]))
        metadatas_to_add.append({
            "mongo_id": str(product["_id"]),
            "name": name,
            "author": author_name,
            "category": category_name,
            "publisher": publisher_name,
            "language": language_name,
            "format": format_name,
            "price": price
        })

    if documents_to_add:
        print(f"Generating embeddings for {len(documents_to_add)} products...")
        embeddings = get_embeddings(documents_to_add)
        products_chroma_collection.add(
            embeddings=embeddings,
            documents=documents_to_add,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"✅ Added {len(documents_to_add)} product vectors to 'product_vectors'.")
    else:
        print("⚠️ No product documents found.")

# ==========================
# 5. XỬ LÝ DỮ LIỆU NEWSTREND
# ==========================
def process_newstrend_data():
    print("\n📰 Processing newstrend data...")
    documents_to_add, ids_to_add, metadatas_to_add = [], [], []

    all_news = newstrend_collection.find({})
    for news_item in all_news:
        title = news_item.get("title", "")
        snippet = news_item.get("contentSnippet", "")
        link = news_item.get("link", "")
        iso_date = news_item.get("isoDate", "")

        combined_text = (
            f"Tiêu đề tin tức: {title}. "
            f"Tóm tắt: {snippet}. "
            f"Ngày đăng: {iso_date}. "
            f"Đường dẫn: {link}"
        )

        documents_to_add.append(combined_text)
        ids_to_add.append(str(news_item["_id"]))
        metadatas_to_add.append({
            "mongo_id": str(news_item["_id"]),
            "title": title,
            "link": link,
            "date": iso_date
        })

    if documents_to_add:
        print(f"Generating embeddings for {len(documents_to_add)} news items...")
        embeddings = get_embeddings(documents_to_add)
        newstrend_chroma_collection.add(
            embeddings=embeddings,
            documents=documents_to_add,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"✅ Added {len(documents_to_add)} newstrend vectors to 'newstrend_vectors'.")
    else:
        print("⚠️ No newstrend documents found.")

# ==========================
# 6. MAIN
# ==========================
if __name__ == "__main__":
    process_products_data()
    process_newstrend_data()
    print("\n🎯 Vectorization process completed successfully!")
    mongo_client.close()
    print("🔒 MongoDB connection closed.")
