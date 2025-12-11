# app/chains/master_chain.py – CHẠY 100%, ASYNC, ỔN ĐỊNH, NHANH NHẤT
from langchain_core.runnables import RunnableParallel, RunnableLambda
from app.chains.behavioral_chain import behavioral_chain
from app.chains.collaborative_chain import collaborative_chain
from app.chains.trending_chain import trending_chain

# TRUYỀN ĐÚNG INPUT CHO 2 CHAIN, TRENDING KHÔNG CẦN
parallel = RunnableParallel(
    behavioral=behavioral_chain,
    collaborative=collaborative_chain,
    trending=trending_chain,  # không cần input → để nguyên runnable
)


def merge_and_deduplicate(results: dict) -> dict:
    combos = []
    seen = set()

    priority_order = ["behavioral", "collaborative", "trending"]

    for source in priority_order:
        result = results.get(source)
        if not result or not hasattr(result, "combos"):
            continue

        for combo in result.combos:
            ids = [str(bid) for bid in combo.book_ids if bid not in seen]
            if len(ids) >= 4:  # ít nhất 4 sách mới hợp lệ
                combos.append(
                    {
                        "title": combo.title,
                        "reason": combo.reason,
                        "book_ids": ids[:5],
                        "source": source,
                    }
                )
                seen.update(ids)

        if len(combos) >= 6:
            break

    # Fallback nếu thiếu
    if len(combos) < 6:
        combos.extend(
            [
                {
                    "title": "Sách đang được yêu thích",
                    "reason": "Hàng ngàn độc giả đã chọn",
                    "book_ids": [],
                    "source": "fallback",
                }
            ]
            * (6 - len(combos))
        )

    return {"dynamic_menu": combos[:6]}


master_chain = parallel | RunnableLambda(merge_and_deduplicate)
