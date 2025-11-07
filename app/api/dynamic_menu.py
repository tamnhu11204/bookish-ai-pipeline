import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.chains.behavioral_chain import chain
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
