# app/api/dynamic_menu.py
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.chains.behavioral_chain import chain as behavioral_chain
from app.chains.collaborative_chain import collaborative_chain
from app.chains.trending_chain import trending_chain
from app.chains.master_chain import master_chain
from app.core.schemas import ComboResponse

router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None


# Các endpoint riêng (nếu cần test từng chain)
@router.post("/recommend/behavioral-chain")
def behavioral_chain_endpoint(req: RecommendRequest):
    try:
        print(
            f"[API] Behavioral chain - user_id: {req.user_id}, session_id: {req.session_id}"
        )
        result = behavioral_chain.invoke(
            {"user_id": req.user_id, "session_id": req.session_id}
        )
        return {"user_id": req.user_id or "guest", "combos": result.combos}
    except Exception as e:
        print(f"[ERROR] Behavioral pipeline failed: {e}")
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


@router.post("/recommend/collaborative-chain")
def collaborative_endpoint(req: RecommendRequest):
    try:
        print(
            f"[API] Collaborative chain - user_id: {req.user_id}, session_id: {req.session_id}"
        )
        result = collaborative_chain.invoke(
            {"user_id": req.user_id, "session_id": req.session_id}
        )
        return {"user_id": req.user_id or "guest", "combos": result.combos}
    except Exception as e:
        print(f"[ERROR] Collaborative failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/trending-chain")
def trending_endpoint():
    try:
        result = trending_chain.invoke({})
        return {"trending_combos": result.combos}
    except Exception as e:
        traceback.print_exc()
        return {"trending_combos": [], "error": str(e)}


# ENDPOINT CHÍNH – MASTER CHAIN (ĐÃ SỬA HOÀN HẢO)
@router.post("/recommend/master")
def master_endpoint(req: RecommendRequest):
    try:
        print(
            f"[MASTER API] Nhận được: user_id={req.user_id}, session_id={req.session_id}"
        )

        # GỌI MASTER CHAIN VỚI CẢ user_id VÀ session_id
        result = master_chain.invoke(
            {
                "user_id": req.user_id,  # có thể là None
                "session_id": req.session_id,  # có thể là None
            }
        )
        return result

    except Exception as e:
        import traceback

        print(f"[MASTER SERVICE] Lỗi: {e}")
        traceback.print_exc()
        return {"dynamic_menu": [], "error": str(e)}
