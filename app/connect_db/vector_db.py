# app/connect_db/vector_db.py
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH")
PRODUCT_SEARCH_COLLECTION = os.getenv(
    "PRODUCT_SEARCH_COLLECTION", "product_search_vectors"
)
PRODUCT_RECOMMEND_COLLECTION = os.getenv(
    "PRODUCT_RECOMMEND_COLLECTION", "product_recommend_vectors"
)
NEWS_COLLECTION_NAME = os.getenv("NEWS_COLLECTION_NAME", "news_vectors")

# TẢI MODEL 1 LẦN
EMBEDDING_MODEL = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))


class ChromaDB:
    _client = None
    _search_collection = None
    _recommend_collection = None
    _news_collection = None

    @classmethod
    def get_search_collection(cls):
        if cls._client is None:
            cls._client = chromadb.PersistentClient(path=CHROMA_PATH)
        if cls._search_collection is None:
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=os.getenv("EMBEDDING_MODEL")
            )
            cls._search_collection = cls._client.get_or_create_collection(
                name=PRODUCT_SEARCH_COLLECTION,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"Search collection ready: {PRODUCT_SEARCH_COLLECTION}")
        return cls._search_collection

    @classmethod
    def get_recommend_collection(cls):
        if cls._client is None:
            cls.get_search_collection()
        if cls._recommend_collection is None:
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=os.getenv("EMBEDDING_MODEL")
            )
            cls._recommend_collection = cls._client.get_or_create_collection(
                name=PRODUCT_RECOMMEND_COLLECTION,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"Recommend collection ready: {PRODUCT_RECOMMEND_COLLECTION}")
        return cls._recommend_collection

    @classmethod
    def get_news_collection(cls):
        if cls._client is None:
            cls.get_search_collection()
        if cls._news_collection is None:
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=os.getenv("EMBEDDING_MODEL")
            )
            cls._news_collection = cls._client.get_or_create_collection(
                name=NEWS_COLLECTION_NAME,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"News collection ready: {NEWS_COLLECTION_NAME}")
        return cls._news_collection

    @classmethod
    def get_model(cls):
        return EMBEDDING_MODEL


# KHỞI TẠO
search_vectors = ChromaDB.get_search_collection()
recommend_vectors = ChromaDB.get_recommend_collection()
news_vectors = ChromaDB.get_news_collection()
get_model = ChromaDB.get_model
