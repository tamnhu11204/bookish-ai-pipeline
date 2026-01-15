# import requests
# import time
# import statistics
# from pymongo import MongoClient

# # Cấu hình
# AI_URL = "http://localhost:8000/ai"  # Thay nếu port khác
# MONGO_URI = "mongodb+srv://tamnhu11204:nhunguyen11204@cluster0.kezkc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Thay URI nếu cần (hoặc dùng MongoDB Atlas)
# DB_NAME = "test"  # Thay tên DB của bạn
# client = MongoClient(MONGO_URI)
# db = client[DB_NAME]
# products = db["products"]


# # 1. Đo thời gian phản hồi
# def measure_latency(num_requests=50):
#     latencies_menu = []
#     latencies_search = []

#     print("Đang đo latency... (có thể mất vài phút)")
#     for i in range(num_requests):
#         # Dynamic Menu (master chain)
#         start = time.time()
#         r_menu = requests.post(
#             f"{AI_URL}/recommend/master", json={}
#         )  # Guest user; thêm "user_id": "xxx" nếu test user cụ thể
#         latencies_menu.append(time.time() - start)

#         # Semantic Search
#         start = time.time()
#         r_search = requests.post(
#             f"{AI_URL}/search", json={"query": "sách phát triển bản thân", "top_k": 10}
#         )
#         latencies_search.append(time.time() - start)

#         if (i + 1) % 10 == 0:
#             print(f"Đã chạy {i + 1}/{num_requests} requests...")

#     print("\n=== THỜI GIAN PHẢN HỒI ===")
#     print(
#         f"Dynamic Menu - Avg: {statistics.mean(latencies_menu):.2f}s | P95: {statistics.quantiles(latencies_menu, n=100)[94]:.2f}s | Max: {max(latencies_menu):.2f}s"
#     )
#     print(
#         f"Semantic Search - Avg: {statistics.mean(latencies_search):.2f}s | P95: {statistics.quantiles(latencies_search, n=100)[94]:.2f}s | Max: {max(latencies_search):.2f}s"
#     )


# # 2. Đo Precision/Recall cho Semantic Search
# # Thay đổi phần này trong hàm measure_search_precision_recall
# def measure_search_precision_recall(
#     queries_with_ground_truth, top_k=10
# ):  # Đổi thành fixed top_k=10
#     precisions = []
#     recalls = []
#     latencies = []

#     print("\nĐang đo Precision/Recall cho Semantic Search (top_k=10)...")
#     for query, truth_ids in queries_with_ground_truth.items():
#         start = time.time()
#         r = requests.post(
#             f"{AI_URL}/search",
#             json={"query": query, "top_k": top_k},  # Fixed 10
#         )
#         latency = time.time() - start
#         latencies.append(latency)

#         results = r.json().get("product_ids", [])[:top_k]  # Chỉ lấy 10

#         truth_set = set(truth_ids)
#         result_set = set(results)

#         hit = len(truth_set & result_set)
#         precision = hit / top_k if results else 0
#         recall = hit / len(truth_ids) if truth_ids else 0

#         precisions.append(precision)
#         recalls.append(recall)

#         print(
#             f"Query: '{query}' | Latency: {latency:.2f}s | "
#             f"Precision@10: {precision:.3f} | Recall@10: {recall:.3f} | Hits: {hit}/{min(10, len(truth_ids))}"
#         )

#     avg_precision = statistics.mean(precisions)
#     avg_recall = statistics.mean(recalls)
#     avg_latency = statistics.mean(latencies)

#     print("\n=== KẾT QUẢ SEMANTIC SEARCH (TOP 10) ===")
#     print(f"Average Precision@10: {avg_precision:.3f}")
#     print(f"Average Recall@10: {avg_recall:.3f}")
#     print(f"Average Latency: {avg_latency:.2f}s")
#     print("→ Nếu Precision@10 ≥ 0.7 và Recall@10 ≥ 0.7 → ĐẠT MỤC TIÊU ĐỒ ÁN!")


# # === BẠN CẦN ĐIỀN GROUND TRUTH TẠI ĐÂY ===
# # Ví dụ: 10 query, mỗi query có 10-20 ID sách đúng (str)
# queries_with_ground_truth = {
#     "sách phát triển bản thân": [
#         "69008b0b4f879b30d5d8f50a",
#         "69008ae94f879b30d5d8f433",
#         "69008aa64f879b30d5d8f293",
#         "69008b0b4f879b30d5d8f509",
#         "69008adb4f879b30d5d8f3dd",
#         "69008ae24f879b30d5d8f408",
#         "69008b034f879b30d5d8f4d7",
#         "68e61e94d5c7bfca1f5477d0",
#         "69008ae54f879b30d5d8f41a",
#         "68e60b881fbb65a475f0fe8f",
#     ],
#     "sách khởi nghiệp": [
#         "68e632ca69241688d8f40789",
#         "68e63402a4758e79c1ea93e2",
#         "68e632c969241688d8f40783",
#         "68e634dfe4857367f2bf9fbc",
#         "68e63440a1c821dcd6ea2a48",
#         "68e632470910fc5c6ee65ae7",
#         "68e632ca69241688d8f4078c",
#         "68e61e94d5c7bfca1f5477d0",
#         "69008ae54f879b30d5d8f41a",
#         "68e60b881fbb65a475f0fe8f",
#     ],
#     "sách phá án hấp dẫn": [
#         "68ee27fd2b63853ada62a7b3",
#         "68ee27fe2b63853ada62a7b9",
#         "68ee27fe2b63853ada62a7b7",
#         "68ee28082b63853ada62a7fb",
#         "68ee280c2b63853ada62a81a",
#         "69008ad14f879b30d5d8f39c",
#         "68fe1630a1ad6bcdc0168a3f",
#         "68e61e94d5c7bfca1f5477d0",
#         "69008ae54f879b30d5d8f41a",
#         "68e60b881fbb65a475f0fe8f",
#     ],
#     "sách tô màu chữa lành": [
#         "68ee19e843073acef346ea26",
#         "68ee19e643073acef346ea1c",
#         "68ee19e543073acef346ea12",
#         "68ee19ef43073acef346ea56",
#         "68ee19ef43073acef346ea52",
#         "68ee19e843073acef346ea2b",
#         "68ee2201f03c049a3903b91f",
#         "68ee19e943073acef346ea32",
#         "68ee19e443073acef346ea0b",
#         "68e60b881fbb65a475f0fe8f",
#     ],
#     "tác phẩm văn học về chiến tranh": [
#         "68e7b556e94ced4063443150",
#         "68fe1611a1ad6bcdc0168967",
#         "68ee173d5e84777eea322477",
#         "68ee1e3a92f466860fb1a5c4",
#         "68e7ac0e9a6f5c07fa3ddba9",
#         "68fe163fa1ad6bcdc0168aaa",
#         "68fe167ba1ad6bcdc0168c41",
#         "68fe1634a1ad6bcdc0168a5b",
#         "69008ae54f879b30d5d8f41a",
#         "68e60b881fbb65a475f0fe8f",
#     ],
# }

# if __name__ == "__main__":
#     measure_latency(num_requests=30)
#     measure_search_precision_recall(queries_with_ground_truth)

# ///////////////////////////////////////////////////////////////////////////////////////

# import chromadb

# client = chromadb.PersistentClient(path="./chroma_db")
# collection_name = "news_vectors"
# collection = client.get_collection(name=collection_name)

# total_count = collection.count()
# print(f"Tổng số documents trong collection '{collection_name}': {total_count}")

# sample = collection.get(
#     limit=10, offset=0, include=["documents", "metadatas", "embeddings"]
# )

# print("\n=== Mẫu 10 documents đầu tiên ===")
# for i in range(len(sample["ids"])):
#     print(f"\nDocument {i+1}:")
#     print(f"  ID:          {sample['ids'][i]}")
#     print(
#         f"  Document:    {sample['documents'][i][:300]}{'...' if len(sample['documents'][i]) > 300 else ''}"
#     )
#     print(f"  Metadata:    {sample['metadatas'][i]}")

#     embeddings = sample.get("embeddings", [])
#     if i < len(embeddings) and embeddings[i] is not None:
#         emb = embeddings[i]
#         print(
#             f"  Embedding:   (vector dài {len(emb)} chiều, ví dụ 10 phần tử đầu: {emb[:10]})"
#         )
#     else:
#         print(
#             "  Embedding:   (không có hoặc rỗng - embeddings không được lưu persistent)"
#         )

# ////////////////////////////////////////////////////////////////////////////////////////////////////////
# import os
# import pickle
# import networkx as nx

# # Đường dẫn file graph (lấy từ code của bạn)
# GRAPH_FILE = "./data/book_graph.gpickle"  # hoặc os.getenv("GRAPH_OUTPUT_FILE")

# if not os.path.exists(GRAPH_FILE):
#     print(f"File graph KHÔNG tồn tại: {GRAPH_FILE}")
#     print("→ Hãy chạy script build_book_graph() trước để tạo file!")
#     exit()

# print(f"Đang load graph từ: {GRAPH_FILE}")
# print(f"Kích thước file: {os.path.getsize(GRAPH_FILE) / (1024*1024):.2f} MB")

# try:
#     with open(GRAPH_FILE, "rb") as f:
#         G = pickle.load(f)

#     print("\n=== THÔNG TIN TỔNG QUAN GRAPH ===")
#     print(f"Số node (sách):          {G.number_of_nodes()}")
#     print(f"Số cạnh (mối quan hệ):   {G.number_of_edges()}")
#     print(f"Graph có hướng không?    {G.is_directed()}")
#     print(f"Mật độ graph:            {nx.density(G):.6f}")

#     # Mẫu node
#     print("\n=== Mẫu 5 node đầu tiên (sách) ===")
#     nodes_list = list(G.nodes(data=True))
#     for node_id, attrs in nodes_list[:5]:
#         print(f"  - Node {node_id}:")
#         print(f"    Tên sách:   {attrs.get('name', 'N/A')}")
#         print(f"    Tác giả:    {attrs.get('author', 'N/A')}")
#         print(f"    Thể loại:   {attrs.get('category', 'N/A')}")

#     # Mẫu cạnh
#     print("\n=== Mẫu 5 cạnh đầu tiên ===")
#     edges_list = list(G.edges(data=True))
#     for u, v, attrs in edges_list[:5]:
#         print(f"  {u} ── {v}")
#         print(f"     Loại quan hệ: {attrs.get('relationship', 'N/A')}")
#         print(f"     Weight:       {attrs.get('weight', 'N/A')}")

#     # Thống kê relationship
#     rel_counts = {}
#     for _, _, data in G.edges(data=True):
#         rel = data.get("relationship", "unknown")
#         rel_counts[rel] = rel_counts.get(rel, 0) + 1

#     print("\n=== Phân bố loại mối quan hệ ===")
#     for rel, count in sorted(rel_counts.items(), key=lambda x: x[1], reverse=True):
#         print(f"  {rel:20}: {count:6} cạnh")

#     # Một số chỉ số thú vị
#     print("\n=== Một số chỉ số nâng cao (tùy chọn) ===")
#     print(
#         f"Độ trung bình (average degree): {sum(dict(G.degree()).values()) / G.number_of_nodes():.2f}"
#     )
#     if G.number_of_nodes() > 0:
#         degrees = [d for n, d in G.degree()]
#         print(
#             f"Node có độ cao nhất: {max(degrees)} (có thể là sách nổi tiếng hoặc tác giả phổ biến)"
#         )

# except Exception as e:
#     print("Lỗi khi load graph:", str(e))
#     print("→ File có thể bị hỏng hoặc không phải graph NetworkX hợp lệ.")

import requests
import time
import statistics

# Cấu hình
AI_URL = "http://localhost:8000/ai"  # Thay nếu deploy lên server khác

# Danh sách query cần đo (bạn có thể thêm/xóa)
queries = [
    "Sách dành cho trẻ vị thành niên bị trầm cảm",
    "Sách dành cho sinh viên mới đi làm cần học cách quản lý tài chính",
    "Gợi ý sách giúp cải thiện kỹ năng giao tiếp trong môi trường công sở",
    "Sách thực hành marketing dành cho chủ shop mới khởi nghiệp",
    "Sách tâm lý chữa lành cho học sinh từng chịu đựng bạo lực học đường",
]

# Số lần lặp đo cho mỗi query (để tính trung bình đáng tin cậy)
REPEATS_PER_QUERY = 10  # Tăng nếu muốn đo kỹ hơn (ví dụ 20)


def measure_search_latency():
    print("\n=== ĐO THỜI GIAN PHẢN HỒI SEMANTIC SEARCH ===")
    print(f"Số query: {len(queries)} | Lặp mỗi query: {REPEATS_PER_QUERY} lần")
    print("Đang đo... (có thể mất vài phút tùy server)\n")

    all_latencies = {}  # Lưu latency từng query
    total_latencies = []

    for query in queries:
        latencies = []
        print(f"Query: '{query}'")

        for i in range(REPEATS_PER_QUERY):
            start = time.time()
            try:
                response = requests.post(
                    f"{AI_URL}/search",
                    json={"query": query, "top_k": 10},
                    timeout=30,  # Ngăn treo nếu server chậm
                )
                latency = time.time() - start
                latencies.append(latency)
                total_latencies.append(latency)

                if response.status_code != 200:
                    print(
                        f"  Lỗi HTTP {response.status_code}: {response.text[:100]}..."
                    )
            except Exception as e:
                print(f"  Lỗi request lần {i+1}: {str(e)}")
                latencies.append(0)  # Ghi nhận lỗi

            time.sleep(0.5)  # Delay nhỏ giữa các request để tránh overload

        if latencies:
            avg = statistics.mean(latencies)
            p95 = (
                statistics.quantiles(latencies, n=100)[94]
                if len(latencies) > 1
                else avg
            )
            min_lat = min(latencies)
            max_lat = max(latencies)
            print(
                f"  Avg: {avg:.3f}s | P95: {p95:.3f}s | Min: {min_lat:.3f}s | Max: {max_lat:.3f}s"
            )
        else:
            print("  Không có request thành công cho query này")

        all_latencies[query] = latencies

    # Tổng kết toàn bộ
    if total_latencies:
        overall_avg = statistics.mean(total_latencies)
        overall_p95 = (
            statistics.quantiles(total_latencies, n=100)[94]
            if len(total_latencies) > 1
            else overall_avg
        )
        print("\n=== TỔNG KẾT SEMANTIC SEARCH ===")
        print(f"Trung bình tất cả query: {overall_avg:.3f}s")
        print(f"P95 tổng: {overall_p95:.3f}s")
        print(
            f"Số request thành công: {len(total_latencies)} / {len(queries) * REPEATS_PER_QUERY}"
        )
    else:
        print("Không có dữ liệu đo được.")


if __name__ == "__main__":
    measure_search_latency()
