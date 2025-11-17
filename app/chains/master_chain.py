# app/chains/master_chain.py
from langchain_core.runnables import RunnableParallel, RunnableLambda
from app.chains.behavioral_chain import chain as behavioral_chain
from app.chains.collaborative_chain import collab_chain
from app.chains.trending_chain import trending_chain
from app.core.schemas import ComboResponse

# 1. Chạy song song (Giữ nguyên)
parallel = RunnableParallel(
    behavioral=behavioral_chain,
    collaborative=collab_chain,
    trending=trending_chain,
)


def merge_results(inputs: dict) -> dict:
    combos = []
    seen = set()

    for chain_name in ["behavioral", "collaborative", "trending"]:
        result = inputs.get(chain_name)
        if not result or not hasattr(result, "combos"):
            continue

        for combo in result.combos:
            unique_ids = [bid for bid in combo.book_ids if bid not in seen]
            if unique_ids:
                combos.append(
                    {
                        "title": combo.title,
                        "reason": combo.reason,
                        "book_ids": unique_ids,
                        "source": chain_name,
                    }
                )
                seen.update(unique_ids)

    return {"dynamic_menu": combos[:9]}


master_chain = parallel | RunnableLambda(merge_results)
