import pymongo
from networkx import Graph
import pickle

# Kết nối đến MongoDB
client = pymongo.MongoClient(
    "mongodb+srv://tamnhu11204:nhunguyen11204@cluster0.kezkc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
db = client["test"]  # Tên database
collection = db["products"]  # Tên collection

# Tạo graph
graph = Graph()

# Lấy tất cả sách từ MongoDB
books = collection.find()

# Xây dựng graph dựa trên tác giả
for book in books:
    book_id = str(book.get("_id"))  # Sử dụng _id làm node
    author = book.get(
        "author", "Unknown"
    )  # Lấy tác giả, mặc định 'Unknown' nếu không có

    # Thêm node cho sách
    graph.add_node(book_id, title=book.get("title", "No Title"))

    # Tìm các sách khác của cùng tác giả để tạo cạnh
    same_author_books = collection.find({"author": author})
    for other_book in same_author_books:
        other_book_id = str(other_book.get("_id"))
        if book_id != other_book_id:  # Tránh tự nối với chính nó
            graph.add_edge(book_id, other_book_id, relationship="same_author")

# Lưu graph vào file pickle
with open("book_graph.pickle", "wb") as f:
    pickle.dump(graph, f)

print("Graph quan hệ đã được xây dựng và lưu vào 'book_graph.pickle'.")
