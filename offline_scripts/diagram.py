import requests
import time
import statistics
from pymongo import MongoClient

# Cấu hình
AI_URL = "http://localhost:8000/ai"  # Thay nếu port khác
MONGO_URI = "mongodb+srv://tamnhu11204:nhunguyen11204@cluster0.kezkc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Thay URI nếu cần (hoặc dùng MongoDB Atlas)
DB_NAME = "test"  # Thay tên DB của bạn
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
products = db["products"]


# 1. Đo thời gian phản hồi
def measure_latency(num_requests=50):
    latencies_menu = []
    latencies_search = []

    print("Đang đo latency... (có thể mất vài phút)")
    for i in range(num_requests):
        # Dynamic Menu (master chain)
        start = time.time()
        r_menu = requests.post(
            f"{AI_URL}/recommend/master", json={}
        )  # Guest user; thêm "user_id": "xxx" nếu test user cụ thể
        latencies_menu.append(time.time() - start)

        # Semantic Search
        start = time.time()
        r_search = requests.post(
            f"{AI_URL}/search", json={"query": "sách phát triển bản thân", "top_k": 10}
        )
        latencies_search.append(time.time() - start)

        if (i + 1) % 10 == 0:
            print(f"Đã chạy {i + 1}/{num_requests} requests...")

    print("\n=== THỜI GIAN PHẢN HỒI ===")
    print(
        f"Dynamic Menu - Avg: {statistics.mean(latencies_menu):.2f}s | P95: {statistics.quantiles(latencies_menu, n=100)[94]:.2f}s | Max: {max(latencies_menu):.2f}s"
    )
    print(
        f"Semantic Search - Avg: {statistics.mean(latencies_search):.2f}s | P95: {statistics.quantiles(latencies_search, n=100)[94]:.2f}s | Max: {max(latencies_search):.2f}s"
    )


# 2. Đo Precision/Recall cho Semantic Search
# Thay đổi phần này trong hàm measure_search_precision_recall
def measure_search_precision_recall(
    queries_with_ground_truth, top_k=10
):  # Đổi thành fixed top_k=10
    precisions = []
    recalls = []
    latencies = []

    print("\nĐang đo Precision/Recall cho Semantic Search (top_k=10)...")
    for query, truth_ids in queries_with_ground_truth.items():
        start = time.time()
        r = requests.post(
            f"{AI_URL}/search",
            json={"query": query, "top_k": top_k},  # Fixed 10
        )
        latency = time.time() - start
        latencies.append(latency)

        results = r.json().get("product_ids", [])[:top_k]  # Chỉ lấy 10

        truth_set = set(truth_ids)
        result_set = set(results)

        hit = len(truth_set & result_set)
        precision = hit / top_k if results else 0
        recall = hit / len(truth_ids) if truth_ids else 0

        precisions.append(precision)
        recalls.append(recall)

        print(
            f"Query: '{query}' | Latency: {latency:.2f}s | "
            f"Precision@10: {precision:.3f} | Recall@10: {recall:.3f} | Hits: {hit}/{min(10, len(truth_ids))}"
        )

    avg_precision = statistics.mean(precisions)
    avg_recall = statistics.mean(recalls)
    avg_latency = statistics.mean(latencies)

    print("\n=== KẾT QUẢ SEMANTIC SEARCH (TOP 10) ===")
    print(f"Average Precision@10: {avg_precision:.3f}")
    print(f"Average Recall@10: {avg_recall:.3f}")
    print(f"Average Latency: {avg_latency:.2f}s")
    print("→ Nếu Precision@10 ≥ 0.7 và Recall@10 ≥ 0.7 → ĐẠT MỤC TIÊU ĐỒ ÁN!")


# === BẠN CẦN ĐIỀN GROUND TRUTH TẠI ĐÂY ===
# Ví dụ: 10 query, mỗi query có 10-20 ID sách đúng (str)
queries_with_ground_truth = {
    "sách phát triển bản thân": [
        "69008b0b4f879b30d5d8f50a",
        "69008ae94f879b30d5d8f433",
        "69008aa64f879b30d5d8f293",
        "69008b0b4f879b30d5d8f509",
        "69008adb4f879b30d5d8f3dd",
        "69008ae24f879b30d5d8f408",
        "69008b034f879b30d5d8f4d7",
        "68e61e94d5c7bfca1f5477d0",
        "69008ae54f879b30d5d8f41a",
        "68e60b881fbb65a475f0fe8f",
    ],
    "sách khởi nghiệp": [
        "68e632ca69241688d8f40789",
        "68e63402a4758e79c1ea93e2",
        "68e632c969241688d8f40783",
        "68e634dfe4857367f2bf9fbc",
        "68e63440a1c821dcd6ea2a48",
        "68e632470910fc5c6ee65ae7",
        "68e632ca69241688d8f4078c",
        "68e61e94d5c7bfca1f5477d0",
        "69008ae54f879b30d5d8f41a",
        "68e60b881fbb65a475f0fe8f",
    ],
    "sách phá án hấp dẫn": [
        "68ee27fd2b63853ada62a7b3",
        "68ee27fe2b63853ada62a7b9",
        "68ee27fe2b63853ada62a7b7",
        "68ee28082b63853ada62a7fb",
        "68ee280c2b63853ada62a81a",
        "69008ad14f879b30d5d8f39c",
        "68fe1630a1ad6bcdc0168a3f",
        "68e61e94d5c7bfca1f5477d0",
        "69008ae54f879b30d5d8f41a",
        "68e60b881fbb65a475f0fe8f",
    ],
    "sách tô màu chữa lành": [
        "68ee19e843073acef346ea26",
        "68ee19e643073acef346ea1c",
        "68ee19e543073acef346ea12",
        "68ee19ef43073acef346ea56",
        "68ee19ef43073acef346ea52",
        "68ee19e843073acef346ea2b",
        "68ee2201f03c049a3903b91f",
        "68ee19e943073acef346ea32",
        "68ee19e443073acef346ea0b",
        "68e60b881fbb65a475f0fe8f",
    ],
    "tác phẩm văn học về chiến tranh": [
        "68e7b556e94ced4063443150",
        "68fe1611a1ad6bcdc0168967",
        "68ee173d5e84777eea322477",
        "68ee1e3a92f466860fb1a5c4",
        "68e7ac0e9a6f5c07fa3ddba9",
        "68fe163fa1ad6bcdc0168aaa",
        "68fe167ba1ad6bcdc0168c41",
        "68fe1634a1ad6bcdc0168a5b",
        "69008ae54f879b30d5d8f41a",
        "68e60b881fbb65a475f0fe8f",
    ],
}

if __name__ == "__main__":
    measure_latency(num_requests=30)  # Đo 30 lần để ổn định
    measure_search_precision_recall(queries_with_ground_truth)
