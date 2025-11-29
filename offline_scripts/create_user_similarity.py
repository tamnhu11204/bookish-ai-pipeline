# offline_scripts/create_user_similarity.py
import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.append(PROJECT_ROOT)

import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.connect_db.mongo_client import orders, user_events
from bson import ObjectId

OUT = "./offline_scripts/data/user_similarity.json"
TOP_K = 100

# Trọng số cho từng hành vi (càng cao = càng quan trọng)
WEIGHTS = {
    "purchase": 5.0,
    "favorite_add": 3.0,
    "add_to_cart": 2.0,
    "compare": 1.5,
    "view": 1.0,
    "view_book": 1.0,
}

def main():
    print("Building rich user behavior vectors (5 events)...")
    user_items = {}
    all_items = set()

    # 1. Lấy từ orders → purchase (trọng số cao nhất)
    for o in orders.find({}, {"user": 1, "orderItems.product": 1}):
        uid = str(o["user"])
        user_items.setdefault(uid, {})
        for it in o.get("orderItems", []):
            pid = str(it.get("product"))
            if pid:
                user_items[uid][pid] = user_items[uid].get(pid, 0) + WEIGHTS["purchase"]
                all_items.add(pid)

    # 2. Lấy từ user_events → view, cart, favorite, compare
    for e in user_events.find({}):
        uid = str(e["userId"])
        pid = str(e.get("productId"))
        action = e["eventType"]
        weight = WEIGHTS.get(action, 0)
        if pid and weight > 0 and uid in user_items:
            user_items[uid][pid] = user_items[uid].get(pid, 0) + weight
            all_items.add(pid)

    # Tạo vector
    item_list = list(all_items)
    idx = {it: i for i, it in enumerate(item_list)}
    vectors = []
    uids = []

    for uid, items in user_items.items():
        if len(items) < 3: continue
        vec = np.zeros(len(item_list))
        for pid, score in items.items():
            vec[idx[pid]] = score
        # Normalize
        if vec.sum() > 0:
            vec = vec / vec.sum()
        vectors.append(vec)
        uids.append(uid)

    print(f"Computing similarity cho {len(uids)} users với 5 loại hành vi...")
    sim = cosine_similarity(vectors)

    result = {}
    for i, uid in enumerate(uids):
        scores = sim[i]
        top = np.argsort(scores)[::-1][1:TOP_K+1]
        similar = {}
        for j in top:
            if scores[j] > 0.1:
                similar[uids[j]] = float(scores[j])
        if similar:
            result[uid] = similar

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"HOÀN TẤT! {len(result)} users → {OUT}")

if __name__ == "__main__":
    main()