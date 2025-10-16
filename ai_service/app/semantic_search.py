# main.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv

load_dotenv()

# Tải cấu hình từ file .env
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PRODUCT_COLLECTION_NAME = "product_vectors"

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Dịch vụ AI Tìm kiếm Sản phẩm",
    description="API cho phép tìm kiếm ngữ nghĩa trên bộ sưu tập sản phẩm sách.",
    version="1.0.0",
)

# --- Tải mô hình và kết nối DB khi khởi động ứng dụng ---
# Việc này giúp mô hình và kết nối sẵn sàng, không cần tải lại mỗi khi có request
try:
    print(f"Đang tải mô hình embedding: '{MODEL_NAME}'...")
    # Tải mô hình embedding vào bộ nhớ.
    model = SentenceTransformer(MODEL_NAME)
    print("✅ Tải mô hình thành công.")
except Exception as e:
    print(f"❌ Lỗi nghiêm trọng: Không thể tải mô hình embedding. {e}")
    model = None

try:
    print(f"Đang kết nối tới ChromaDB tại: {CHROMA_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Kết nối tới collection sản phẩm đã được tạo bởi script vector hóa
    products_chroma_collection = chroma_client.get_collection(
        name=PRODUCT_COLLECTION_NAME
    )
    print(f"✅ Kết nối thành công tới collection '{PRODUCT_COLLECTION_NAME}'.")
except Exception as e:
    print(f"❌ Lỗi: Không thể kết nối tới collection '{PRODUCT_COLLECTION_NAME}'.")
    print("👉 Vui lòng chắc chắn rằng bạn đã chạy script vector hóa dữ liệu trước.")
    products_chroma_collection = None


# Model cho request body, tuân thủ yêu cầu của task
class SearchQuery(BaseModel):
    query: str = Field(
        ..., description="Chuỗi văn bản cần tìm kiếm.", example="sách về kinh tế vĩ mô"
    )
    top_k: int = Field(20, gt=0, le=100, description="Số lượng kết quả trả về.")


# Model cho response body
class SearchResponse(BaseModel):
    product_ids: list[str]


# Tạo API endpoint POST /ai/search.
@app.post(
    "/ai/search",
    response_model=SearchResponse,
    summary="Tìm kiếm sản phẩm theo ngữ nghĩa",
)
async def search_products(search_request: SearchQuery):
    """
    Endpoint này nhận một chuỗi tìm kiếm và trả về danh sách các ID sản phẩm
    có nội dung tương đồng nhất về mặt ngữ nghĩa.
    """
    if not model or not products_chroma_collection:
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ chưa sẵn sàng. Vui lòng kiểm tra log để biết thêm chi tiết.",
        )

    try:
        # Nhận chuỗi tìm kiếm (query) từ request body (được xử lý bởi FastAPI)

        # Sử dụng mô hình để vector hóa chuỗi query của người dùng.
        print(f"Đang vector hóa query: '{search_request.query}'")
        query_embedding = model.encode(search_request.query).tolist()

        # Sử dụng vector truy vấn để truy vấn vào collection sách trong ChromaDB
        # và lấy ra top k ID của các cuốn sách có vector tương đồng nhất.
        print(f"Đang truy vấn ChromaDB để lấy top {search_request.top_k} kết quả...")
        results = products_chroma_collection.query(
            query_embeddings=[query_embedding], n_results=search_request.top_k
        )

        # Trả về một mảng JSON chứa danh sách các ID sách này.
        # ID được lấy từ kết quả truy vấn, chúng chính là các _id từ MongoDB.
        product_ids = results.get("ids", [[]])[0]
        print(f"✅ Tìm thấy {len(product_ids)} kết quả.")

        return {"product_ids": product_ids}

    except Exception as e:
        print(f"❌ Đã xảy ra lỗi trong quá trình tìm kiếm: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ nội bộ: {e}")


@app.get("/", summary="Kiểm tra trạng thái dịch vụ")
def read_root():
    return {"status": "Dịch vụ AI tìm kiếm ngữ nghĩa đang hoạt động."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
