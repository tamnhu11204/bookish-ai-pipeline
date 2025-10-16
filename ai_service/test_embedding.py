from sentence_transformers import SentenceTransformer
import torch

def test_embedding_model():
    print("Loading Vietnamese embedding model...")
    # Sử dụng mô hình đã được huấn luyện sẵn cho tiếng Việt
    # LƯU Ý: Lần chạy đầu tiên sẽ mất thời gian để tải mô hình về máy.
    try:
        model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")
        print("Model loaded successfully!")

        # Tạo một vài câu tiếng Việt mẫu
        sentences = [
            "Chào buổi sáng",
            "Thời tiết hôm nay đẹp quá",
            "Tôi muốn ăn phở",
            "Thực đơn đa dạng món ăn",
            "Hôm nay trời mưa",
            "Anh ấy là một đầu bếp giỏi"
        ]
        print("\nSample sentences for embedding:")
        for s in sentences:
            print(f"- {s}")

        # Dùng model.encode() để chuyển các câu này thành vector
        print("\nGenerating embeddings...")
        embeddings = model.encode(sentences)
        print("Embeddings generated successfully!")

        # In ra kích thước (shape) của vector để xác nhận.
        print(f"\nShape of embeddings: {embeddings.shape}")
        # Kích thước expected là (số_câu, kích_thước_vector). Ví dụ: (6, 768)
        # Kích thước 768 là phổ biến cho các mô hình sentence-transformer.

        # In ra embedding của câu đầu tiên làm ví dụ
        print("\nFirst sentence embedding (first 5 dimensions):")
        print(embeddings[0][:5])

        # Optional: Kiểm tra độ tương đồng giữa hai câu
        from sklearn.metrics.pairwise import cosine_similarity
        
        embedding_phophuc = model.encode(["phở phở phở phở phở phở phở phở phở phở"])
        embedding_bun = model.encode(["bún bún bún bún bún bún bún bún bún bún"])

        similarity = cosine_similarity(embedding_phophuc, embedding_bun)
        print(f"\nSimilarity between 'phở phở phở phở phở phở phở phở phở phở' and 'bún bún bún bún bún bún bún bún bún bún': {similarity[0][0]:.4f}")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure you have an active internet connection for the first run to download the model.")
        print("Also, check if 'sentence-transformers' is correctly installed.")

if __name__ == "__main__":
    test_embedding_model()