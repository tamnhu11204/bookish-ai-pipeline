import json
import os
import sys
import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# --- CẤU HÌNH ---
MONGODB_URI = "mongodb+srv://tamnhu11204:nhunguyen11204@cluster0.kezkc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "test"
JSON_DIR = "./"
BATCH_SIZE = 24

# Danh sách file JSON cụ thể để import
JSON_FILES = [
    "crawled_books_chinh_tri.json",
    # Thêm file khác nếu cần, ví dụ: "crawled_books_van_hoc.json"
]


def connect_to_mongodb(uri):
    """Kết nối đến MongoDB."""
    try:
        client = MongoClient(uri)
        client.admin.command("ismaster")
        print("Kết nối MongoDB thành công!")
        return client
    except ConnectionFailure as e:
        print(f"Lỗi kết nối MongoDB: {e}")
        return None


def update_book_descriptions(client, db_name, collection_name, json_files, batch_size):
    """Cập nhật description cho các sách đã tồn tại trong collection từ file JSON."""
    db = client[db_name]
    collection = db[collection_name]

    total_updated = 0
    total_skipped = 0
    total_not_found = 0

    for json_file in json_files:
        json_path = os.path.join(JSON_DIR, json_file)
        if not os.path.exists(json_path):
            print(f"File {json_path} không tồn tại. Bỏ qua.")
            continue

        print(f"\nĐang xử lý file: {json_path}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Lỗi đọc JSON từ {json_path}: {e}")
            continue

        print(f"Đã đọc {len(data)} documents từ {json_path}.")

        # Xử lý từng batch
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            for book in batch:
                book_name = book.get("name", "Không có tên")
                description = book.get("description", "")

                # Tìm sách trong database bằng tên
                existing_book = collection.find_one({"name": book_name})

                if not existing_book:
                    print(f"Bỏ qua sách '{book_name}' vì không tồn tại trong database.")
                    total_not_found += 1
                    continue

                # Kiểm tra description hiện tại
                current_description = existing_book.get("description")
                if current_description and current_description.strip():
                    print(f"Bỏ qua sách '{book_name}' vì đã có description.")
                    total_skipped += 1
                    continue

                # Kiểm tra description từ JSON
                if not description or not description.strip():
                    print(f"Bỏ qua sách '{book_name}' vì description trong JSON rỗng.")
                    total_skipped += 1
                    continue

                # Cập nhật description
                try:
                    result = collection.update_one(
                        {"name": book_name}, {"$set": {"description": description}}
                    )
                    if result.modified_count > 0:
                        print(f"Đã cập nhật description cho sách '{book_name}'")
                        total_updated += 1
                    else:
                        print(
                            f"Không cập nhật được description cho sách '{book_name}' (không thay đổi)."
                        )
                        total_skipped += 1
                except Exception as e:
                    print(f"Lỗi cập nhật description cho sách '{book_name}': {e}")
                    total_skipped += 1
                    continue

            print(
                f"Đã xử lý batch {i//batch_size + 1} từ {json_file}: {len(batch)} documents."
            )
            time.sleep(1)  # Nghỉ ngắn để tránh overload Free Tier

    print(f"\nHoàn tất cập nhật: {total_updated} sách được cập nhật description.")
    print(f"Số sách bỏ qua (đã có description, JSON rỗng, hoặc lỗi): {total_skipped}")
    print(f"Số sách không tìm thấy trong database: {total_not_found}")
    count = collection.count_documents({})
    print(f"Tổng số documents trong collection '{collection_name}': {count}")

    client.close()


if __name__ == "__main__":
    # Nếu có tham số command line, dùng nó thay cho JSON_FILES
    if len(sys.argv) > 1:
        JSON_FILES = sys.argv[1:]

    # Kiểm tra file tồn tại
    json_files = [f for f in JSON_FILES if os.path.exists(os.path.join(JSON_DIR, f))]
    if not json_files:
        print(f"Không tìm thấy file JSON nào trong danh sách {JSON_FILES}.")
        sys.exit(1)

    client = connect_to_mongodb(MONGODB_URI)
    if client:
        update_book_descriptions(client, DB_NAME, "products", json_files, BATCH_SIZE)
