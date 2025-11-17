# app/api/dynamic_menu.py
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.chains.behavioral_chain import chain as behavioral_chain
from app.chains.collaborative_chain import collab_chain
from app.chains.trending_chain import trending_chain
from app.chains.master_chain import master_chain
from app.core.schemas import ComboResponse
from app.core.schemas import RecommendRequest as MasterReq

router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: str


@router.post("/recommend/behavioral-chain")
def behavioral_chain_endpoint(req: RecommendRequest):
    try:
        print(f"[API] Calling behavioral chain with user_id: {req.user_id}")
        # Truyền vào dict theo cấu trúc của chain
        result = behavioral_chain.invoke({"user_id": req.user_id})
        return {"user_id": req.user_id, "combos": result.combos}
    except Exception as e:
        print(f"[ERROR] Behavioral pipeline failed: {e}")
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


@router.post("/recommend/collaborative-chain")
def collaborative_endpoint(req: RecommendRequest):
    try:
        print(f"[API] Calling collaborative chain with user_id: {req.user_id}")
        # Truyền vào dict theo cấu trúc của chain
        result = collab_chain.invoke({"user_id": req.user_id})
        return {"user_id": req.user_id, "combos": result.combos}
    except Exception as e:
        print(f"[ERROR] Collaborative failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# SỬA: Chuyển sang đồng bộ
@router.post("/recommend/trending-chain")
def trending_endpoint():
    try:
        # SỬA: Dùng .invoke()
        result = trending_chain.invoke({})
        # SỬA: Trả về cấu trúc nhất quán
        return {"trending_combos": result.combos}
    except Exception as e:
        traceback.print_exc()
        return {"trending_combos": [], "error": str(e)}


# SỬA: Chuyển sang đồng bộ
@router.post("/recommend/master")
def master_endpoint(req: MasterReq):
    try:
        # SỬA: Dùng .invoke()
        # Input {"user_id": req.user_id} sẽ được RunnableParallel
        # tự động truyền xuống các chain con.
        result = master_chain.invoke({"user_id": req.user_id})
        return result
    except Exception as e:
        print(f"[ERROR] Master chain failed: {e}")
        traceback.print_exc()
        return {"dynamic_menu": [], "error": str(e)}
