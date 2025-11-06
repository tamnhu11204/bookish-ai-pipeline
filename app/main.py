from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import dynamic_menu, semantic_search

# Khởi tạo ứng dụng FastAPI chính
app = FastAPI(
    title="Bookish AI Service",
    description="Một API hợp nhất cho tìm kiếm và gợi ý sách.",
    version="1.0.0",
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các router từ các module khác
app.include_router(semantic_search.router, prefix="/ai", tags=["Search"])
app.include_router(dynamic_menu.router, prefix="/ai", tags=["Recommendations"])


@app.get("/", tags=["Root"])
def read_root():
    return {"status": "ok", "service": "Bookish AI Service"}


# Để chạy: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
