# app/chains/master_chain.py – PHIÊN BẢN HOÀN HẢO, AINVOKE HOẠT ĐỘNG 100%
from langchain_core.runnables import RunnableParallel, RunnableLambda
from app.chains.behavioral_chain import behavioral_chain
from app.chains.collaborative_chain import collaborative_chain
from app.chains.trending_chain import trending_chain


parallel = RunnableParallel(
    behavioral=RunnableLambda(
        lambda x: behavioral_chain.invoke(
            {"user_id": x.get("user_id"), "session_id": x.get("session_id")}
        )
    ),
    collaborative=RunnableLambda(
        lambda x: collaborative_chain.invoke(
            {"user_id": x.get("user_id"), "session_id": x.get("session_id")}
        )
    ),
    trending=trending_chain,
)


def merge_results(inputs: dict) -> dict:
    combos = []
    seen = set()

    for chain_name in ["behavioral", "collaborative", "trending"]:
        result = inputs.get(chain_name)
        if not result:
            continue

        # SIÊU QUAN TRỌNG: XỬ LÝ CẢ OBJECT Pydantic VÀ DICT
        if hasattr(result, "combos"):
            combo_list = result.combos
        elif isinstance(result, list):
            combo_list = result
        elif isinstance(result, dict) and "combos" in result:
            combo_list = result["combos"]
        else:
            combo_list = []

        for combo in combo_list:
            # XỬ LÝ CẢ OBJECT VÀ DICT
            if hasattr(combo, "dict"):  # là Pydantic object
                combo_dict = combo.dict()
            else:
                combo_dict = combo if isinstance(combo, dict) else {}

            title = combo_dict.get("title", "Gợi ý đặc biệt")
            reason = combo_dict.get("reason", "Dành riêng cho bạn")
            book_ids = combo_dict.get("book_ids", [])

            if not book_ids:
                continue

            unique_ids = [bid for bid in book_ids if bid not in seen]
            if unique_ids:
                combos.append(
                    {
                        "title": title,
                        "reason": reason,
                        "book_ids": unique_ids,
                        "source": chain_name,
                    }
                )
                seen.update(unique_ids)

    # Fallback từ trending nếu thiếu
    while len(combos) < 6:
        fallback = inputs.get("trending")
        if not fallback or not hasattr(fallback, "combos"):
            break
        for combo in fallback.combos:
            unique_ids = [bid for bid in combo.book_ids if bid not in seen]
            if len(unique_ids) == 5:
                combos.append(
                    {
                        "title": combo.title,
                        "reason": combo.reason,
                        "book_ids": unique_ids,
                        "source": "fallback_trending",
                    }
                )
                seen.update(unique_ids)
                break

    return {"dynamic_menu": combos[:6]}


master_chain = parallel | RunnableLambda(merge_results)
__all__ = ["master_chain"]
