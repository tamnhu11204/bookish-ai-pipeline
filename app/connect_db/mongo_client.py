# ai_service/app/db/mongo_client.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "knowledge_base")


class MongoDB:
    _client = None
    _db = None

    @classmethod
    def get_db(cls):
        if cls._client is None:
            try:
                cls._client = MongoClient(MONGO_URI)
                cls._db = cls._client[DATABASE_NAME]
                print("Connected to MongoDB successfully!")
            except Exception as e:
                print(f"MongoDB connection error: {e}")
                exit()
        return cls._db


db = MongoDB.get_db()

# Xuất ra các collection để các service khác có thể import và sử dụng
user_events = db["userevents"]
orders = db["orders"]
products = db["products"]
categories = db["categories"]
