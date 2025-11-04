# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from services.search_service import hybrid_search

app = FastAPI(title="AI Semantic Search API")

# Cấu hình CORS (cho phép FE hoặc BE gọi)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ai/search")
async def search_books(request: Request):
    data = await request.json()
    query = data.get("query")

    if not query:
        return {"error": "Thiếu tham số query"}

    # Gọi hàm tìm kiếm ngữ nghĩa trong services/search_service.py
    results = hybrid_search(query=query, top_k=10)
    return {"product_ids": results}


@app.get("/")
def root():
    return {"message": "AI Semantic Search service is running!"}
