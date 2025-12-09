# app/tools/cache.py – PHIÊN BẢN HOÀN HẢO, KHÔNG BAO GIỜ LỖI HASH NỮA
import json
from functools import lru_cache
from typing import List, Any


@lru_cache(maxsize=3000)
def _get_groups_cached(sorted_ids_tuple: tuple) -> str:
    """
    Hàm nội bộ được cache – chỉ nhận tuple (hashable)
    """
    if not sorted_ids_tuple:
        return "[]"

    try:
        from app.tools.graph_grouper import GraphGrouperTool

        raw_groups = GraphGrouperTool().invoke({"product_ids": list(sorted_ids_tuple)})
        return json.dumps(raw_groups, ensure_ascii=False)
    except Exception as e:
        print(f"[CACHE] GraphGrouper lỗi → dùng fallback: {e}")
        books = list(sorted_ids_tuple)[:10]
        fallback = [
            {"title": "Khám phá thêm", "books": books[:5]},
            {
                "title": "Sách được yêu thích",
                "books": books[5:10] if len(books) > 5 else books[:5],
            },
        ]
        return json.dumps(fallback, ensure_ascii=False)


def get_cached_groups(product_ids: List[str]) -> str:
    """
    HÀM DUY NHẤT BẠN SẼ GỌI TỪ CÁC CHAIN
    → TỰ ĐỘNG CHUYỂN LIST → TUPLE → CACHE AN TOÀN
    """
    if not product_ids:
        return "[]"

    # Chuyển thành tuple đã sort → hashable
    cache_key = tuple(sorted(set(product_ids)))
    return _get_groups_cached(cache_key)
