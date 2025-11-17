# offline_scripts/create_item_similarity.py
import sys
import os
import json
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# FIX PATH
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.append(PROJECT_ROOT)

# IMPORT ĐÚNG COLLECTION
from app.connect_db.mongo_client import orders  # ← Đảm bảo collection đúng tên

load_dotenv()
OUT_PATH = os.getenv("ITEM_SIM_PATH", "./offline_scripts/data/item_similarity.json")
TOP_K = int(os.getenv("ITEM_SIM_TOPK", "50"))


def extract_purchase_history():
    rows = []
    print("Đang quét collection `orders`...")
    total = 0
    for order in orders.find({}, {"user": 1, "orderItems": 1}):
        total += 1
        user_id = order.get("user")
        if not user_id:
            continue
        user_id = str(user_id)

        for item in order.get("orderItems", []):
            product_id = item.get("product")
            if product_id:
                rows.append({"user_id": user_id, "item_id": str(product_id)})
    print(f"Đã quét {total} đơn hàng → {len(rows)} lượt mua")
    return pd.DataFrame(rows)


# === PHẦN CÒN LẠI GIỮ NGUYÊN ===
def build_item_user_matrix(df):
    if df.empty:
        return None, [], {}
    users = df["user_id"].unique().tolist()
    items = df["item_id"].unique().tolist()
    user2idx = {u: i for i, u in enumerate(users)}
    item2idx = {it: i for i, it in enumerate(items)}
    row_idx = df["item_id"].map(item2idx).values
    col_idx = df["user_id"].map(user2idx).values
    data = np.ones(len(df), dtype=np.float32)
    mat = coo_matrix((data, (row_idx, col_idx)), shape=(len(items), len(users)))
    return mat, items, item2idx


def compute_similarity(mat, items, top_k=50):
    if mat is None:
        return {}
    print(f"Tính similarity cho {len(items)} sách...")
    dense = mat.toarray()
    sim = cosine_similarity(dense)
    result = {}
    for i, item_id in enumerate(items):
        scores = [
            (items[j], float(sim[i][j]))
            for j in range(len(items))
            if j != i and sim[i][j] > 0.01
        ]
        top = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
        result[item_id] = {other_id: round(score, 4) for other_id, score in top}
    return result


def main():
    df = extract_purchase_history()
    if df.empty:
        print("Không có dữ liệu mua hàng!")
        return
    print(
        f"Trích xuất: {len(df)} lượt | {df['user_id'].nunique()} người | {df['item_id'].nunique()} sách"
    )
    mat, items, _ = build_item_user_matrix(df)
    sim = compute_similarity(mat, items, top_k=TOP_K)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sim, f, ensure_ascii=False, indent=2)
    print(f"HOÀN TẤT! Lưu tại {OUT_PATH}")


if __name__ == "__main__":
    main()
