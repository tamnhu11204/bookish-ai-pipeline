# app/connect_db/vector_db.py
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH")
PRODUCT_COLLECTION_NAME = os.getenv("PRODUCT_COLLECTION_NAME", "product_vectors")


class ChromaDB:
    _client = None
    _collection = None

    @classmethod
    def get_collection(cls):
        if cls._client is None:
            try:
                cls._client = chromadb.PersistentClient(path=CHROMA_PATH)
                cls._collection = cls._client.get_or_create_collection(
                    name=PRODUCT_COLLECTION_NAME,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=os.getenv("EMBEDDING_MODEL")
                    ),
                )
                print(f"(API Service) Connected to ChromaDB at '{CHROMA_PATH}'")
            except Exception as e:
                print(f"(API Service) ChromaDB connection error: {e}")
                raise RuntimeError("Could not connect to ChromaDB") from e
        return cls._collection


# KHỞI TẠO NGAY ĐỂ ĐẢM BẢO
product_vectors = ChromaDB.get_collection()
