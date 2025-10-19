import os
from typing import List
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Cấu hình từ file .env
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PRODUCT_COLLECTION_NAME = "product_vectors"


# Lớp ngoại lệ tùy chỉnh
class SearchServiceError(Exception):
    """Lớp ngoại lệ tùy chỉnh cho các lỗi trong SearchService."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Khởi tạo mô hình và kết nối ChromaDB
try:
    print(f"🔹 Đang tải mô hình embedding: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"🔹 Đang kết nối tới ChromaDB tại: {CHROMA_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_collection(PRODUCT_COLLECTION_NAME)
    print(
        f"✅ Kết nối thành công tới collection '{PRODUCT_COLLECTION_NAME}' & mô hình đã tải."
    )
except Exception as e:
    print(f"❌ Lỗi nghiêm trọng: Không thể khởi tạo dịch vụ tìm kiếm: {e}")
    model = None
    collection = None


def semantic_search(query: str, top_k: int = 20) -> List[str]:
    """
    Hàm thực hiện tìm kiếm ngữ nghĩa trong ChromaDB.

    Args:
        query (str): Chuỗi truy vấn tìm kiếm.
        top_k (int): Số lượng kết quả trả về (mặc định: 20, giới hạn: 1-100).

    Returns:
        List[str]: Danh sách các ID sản phẩm tương đồng.

    Raises:
        SearchServiceError: Nếu đầu vào không hợp lệ hoặc có lỗi trong quá trình tìm kiếm.
    """
    # Kiểm tra trạng thái mô hình và collection
    if not model or not collection:
        raise SearchServiceError(
            "Dịch vụ chưa sẵn sàng. Vui lòng kiểm tra log để biết thêm chi tiết.",
            status_code=503,
        )

    # Xác thực đầu vào
    if not query or not isinstance(query, str) or query.strip() == "":
        raise SearchServiceError("Chuỗi truy vấn không được rỗng.", status_code=400)

    if not isinstance(top_k, int):
        raise SearchServiceError("top_k phải là một số nguyên.", status_code=400)

    if top_k < 1 or top_k > 100:
        raise SearchServiceError(
            "top_k phải nằm trong khoảng từ 1 đến 100.", status_code=400
        )

    try:
        # Vector hóa chuỗi truy vấn
        print(f"🔹 Đang vector hóa query: '{query}'")
        query_emb = model.encode(query).tolist()

        # Truy vấn ChromaDB
        print(f"🔹 Đang truy vấn ChromaDB để lấy top {top_k} kết quả...")
        results = collection.query(query_embeddings=[query_emb], n_results=top_k)
        ids = results.get("ids", [[]])[0]
        print(f"✅ Tìm thấy {len(ids)} kết quả.")

        return ids

    except Exception as e:
        print(f"❌ Lỗi trong semantic_search: {e}")
        raise SearchServiceError(f"Lỗi trong quá trình tìm kiếm: {e}", status_code=500)
