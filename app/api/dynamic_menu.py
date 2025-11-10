import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.chains.behavioral_chain import chain
from app.chains.collaborative_chain import collab_chain
from app.core.schemas import ComboResponse
import json

router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: str


@router.post("/recommend/behavioral-chain")
def behavioral_chain_endpoint(req: RecommendRequest):
    try:
        print(f"[API] Calling chain with user_id: {req.user_id}")
        result = chain.invoke({"user_id": req.user_id})
        # result đã là ComboResponse object → chuyển dict
        return {"user_id": req.user_id, "combos": result.combos}
    except Exception as e:
        print(f"[ERROR] Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(500, detail=str(e))
    

@router.post("/recommend/collaborative-chain")
def collaborative_endpoint(req: RecommendRequest):
    try:
        print(f"[API] Collaborative → user_id: {req.user_id}")
        result = collab_chain.invoke({"user_id": req.user_id})
        return {
            "user_id": req.user_id,
            "recommendations": result  # collab_chain trả dict/list
        }
    except Exception as e:
        print(f"[ERROR] Collaborative failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Collaborative chain failed")
