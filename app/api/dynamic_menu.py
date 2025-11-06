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
        result = chain.invoke({"user_id": req.user_id})
        combos = json.loads(result)
        return {"user_id": req.user_id, "combos": combos}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
