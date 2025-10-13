import json
import os
import re
import sys
import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError

# --- CẤU HÌNH ---
MONGODB_URI = "mongodb+srv://tamnhu11204:nhunguyen11204@cluster0.kezkc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "test"
JSON_DIR = "./"
BATCH_SIZE = 24

# Danh sách file JSON cụ thể để import
JSON_FILES = [
    "crawled_books_truyen_thieu_nhi_page_19.json",
    # Thêm file khác nếu cần, ví dụ: "crawled_books_van_hoc.json"
]

# Prefix cho code của các collection
PREFIXES = {
    "products": "PD",
    "authors": "AU",
    "publishers": "PB",
    "suppliers": "SP",
    "languages": "LG",
    "formats": "FM",
    "categories": "CT",
}


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


def get_next_code(collection, prefix):
    """Tạo code sequential với prefix (ví dụ: PD000001)."""
    regex = re.compile(f"^{re.escape(prefix)}\\d{{6}}$")
    max_doc = collection.find_one({"code": {"$regex": regex}}, sort=[("code", -1)])
    num = int(max_doc["code"][len(prefix) :]) + 1 if max_doc else 1
    return f"{prefix}{num:06d}"


def create_slug(name):
    """Tạo slug từ tên (cho Category)."""
    slug = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    slug = re.sub(r"[\s]+", "-", slug)
    return slug if slug else "khong-xac-dinh"


def get_or_create_ref(collection, name_field, name_value, prefix, extra_fields=None):
    """Tìm hoặc tạo mới document với code sequential."""
    default_name = {
        "author_name": "Không có tác giả",
        "publisher_name": "Không có NXB",
        "supplier_name": "Không có nhà cung cấp",
        "category_name": "Không xác định",
        "language_name": "Tiếng Việt",
        "format_name": "Bìa mềm",
    }.get(name_field, "Không xác định")
    name_value = name_value or default_name

    doc = collection.find_one({name_field: name_value})
    if doc:
        return doc["_id"]

    code = get_next_code(collection, prefix)
    new_doc = {"code": code, name_field: name_value, **(extra_fields or {})}
    try:
        result = collection.insert_one(new_doc)
        return result.inserted_id
    except DuplicateKeyError:
        new_doc["code"] = get_next_code(collection, prefix)
        result = collection.insert_one(new_doc)
        return result.inserted_id


def map_book_data(book, db):
    """Chuyển đổi dữ liệu từ JSON crawl sang schema Product."""
    book_name = book.get("name", "Không có tên")
    # Kiểm tra trùng tên
    if db["products"].find_one({"name": book_name}):
        print(f"Bỏ qua sách '{book_name}' vì tên đã tồn tại.")
        return None

    # Lấy code mới ngay trước khi insert để đảm bảo unique
    code = get_next_code(db["products"], PREFIXES["products"])

    author_id = get_or_create_ref(
        db["authors"],
        "name",
        book.get("author_name"),
        PREFIXES["authors"],
        {"info": "", "img": ""},
    )
    publisher_id = get_or_create_ref(
        db["publishers"],
        "name",
        book.get("publisher_name"),
        PREFIXES["publishers"],
        {"note": "", "img": ""},
    )
    supplier_id = get_or_create_ref(
        db["suppliers"],
        "name",
        book.get("supplier_name"),
        PREFIXES["suppliers"],
        {"note": "", "img": ""},
    )
    language_id = get_or_create_ref(
        db["languages"],
        "name",
        book.get("language_name"),
        PREFIXES["languages"],
        {"note": ""},
    )
    format_id = get_or_create_ref(
        db["formats"],
        "name",
        book.get("format_name"),
        PREFIXES["formats"],
        {"note": ""},
    )
    category_id = get_or_create_ref(
        db["categories"],
        "name",
        book.get("category_name"),
        PREFIXES["categories"],
        {
            "note": "",
            "img": "",
            "slug": create_slug(book.get("category_name", "Không xác định")),
            "parent": None,
        },
    )

    return {
        "code": code,
        "name": book_name,
        "author": author_id,
        "publishYear": book.get("publish_year", None),
        "weight": book.get("weight_gr", 0),
        "dimensions": book.get("dimensions_str", ""),
        "page": book.get("page", 0),
        "description": book.get("description", ""),
        "price": book.get("price", 0),
        "discount": book.get("discount", 0),
        "stock": 0,
        "img": book.get("img", []),
        "star": 0,
        "favorite": 0,
        "view": 0,
        "sold": 0,
        "feedbackCount": 0,
        "isDeleted": False,
        "deletedAt": None,
        "publisher": publisher_id,
        "language": language_id,
        "format": format_id,
        "category": category_id,
        "supplier": supplier_id,
    }


def import_data_to_mongodb(client, db_name, collection_name, json_files, batch_size):
    """Import dữ liệu từ các file JSON vào MongoDB."""
    db = client[db_name]
    collection = db[collection_name]

    # Tạo index để đảm bảo unique và tăng tốc query
    for coll_name, prefix in PREFIXES.items():
        db[coll_name].create_index("code", unique=True)
        if coll_name != "products":
            db[coll_name].create_index("name", unique=True)
        if coll_name == "categories":
            db[coll_name].create_index("slug", unique=True)
    db["products"].create_index("name", unique=True)

    total_inserted = 0
    skipped_books = 0
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

        mapped_data = []
        for book in data:
            try:
                mapped_book = map_book_data(book, db)
                if mapped_book:
                    mapped_data.append(mapped_book)
                else:
                    skipped_books += 1
            except Exception as e:
                print(f"Lỗi ánh xạ sách '{book.get('name', 'Unknown')}': {e}")
                skipped_books += 1
                continue

        # Insert từng sách để đảm bảo code tăng dần
        for i in range(0, len(mapped_data), batch_size):
            batch = mapped_data[i : i + batch_size]
            for book in batch:
                try:
                    # Gọi get_next_code ngay trước insert để đảm bảo code mới nhất
                    book["code"] = get_next_code(db["products"], PREFIXES["products"])
                    result = collection.insert_one(book)
                    total_inserted += 1
                    print(f"Đã insert sách '{book['name']}' (code: {book['code']})")
                except DuplicateKeyError as e:
                    print(f"Bỏ qua sách '{book['name']}' do trùng key: {e}")
                    skipped_books += 1
                    continue
                except Exception as e:
                    print(f"Lỗi insert sách '{book['name']}': {e}")
                    skipped_books += 1
                    continue
            print(
                f"Đã xử lý batch {i//batch_size + 1} từ {json_file}: {len(batch)} documents."
            )
            time.sleep(1)  # Nghỉ ngắn để tránh overload Free Tier

    print(
        f"\nHoàn tất import: {total_inserted} documents vào collection '{collection_name}'."
    )
    print(f"Số sách bị bỏ qua do trùng tên hoặc lỗi: {skipped_books}")
    count = collection.count_documents({})
    print(f"Tổng số documents trong collection 'products': {count}")

    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {
            "$lookup": {
                "from": "categories",
                "localField": "_id",
                "foreignField": "_id",
                "as": "category_info",
            }
        },
        {
            "$project": {
                "category_name": {"$arrayElemAt": ["$category_info.name", 0]},
                "count": 1,
            }
        },
        {"$sort": {"category_name": 1}},
    ]
    category_counts = collection.aggregate(pipeline)
    print("\nSố sách theo danh mục:")
    for cat in category_counts:
        print(f"{cat['category_name']}: {cat['count']} sách")

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
        import_data_to_mongodb(client, DB_NAME, "products", json_files, BATCH_SIZE)
