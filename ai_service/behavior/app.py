# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from recommender_core import generate_behavior_recommendations
import uvicorn

app = FastAPI(title="AI Recommendation Service", version="1.0")

class RecommendRequest(BaseModel):
    user_id: str

@app.post("/recommend/user-behavior")
def recommend_user_behavior(req: RecommendRequest):
    """
    API gợi ý sách dựa trên hành vi người dùng
    """
    try:
        result = generate_behavior_recommendations(req.user_id)
        if not result or len(result) == 0:
            return {"message": "Không tìm thấy gợi ý phù hợp", "recommendations": []}
        return {"user_id": req.user_id, "recommendations": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gợi ý: {e}")

@app.get("/")
def root():
    return {"status": "ok", "service": "AI Recommendation Service"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
