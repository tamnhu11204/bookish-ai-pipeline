# offline_scripts/cleanup_news.py
import schedule
from datetime import datetime, timedelta
from app.connect_db.vector_db import news_vectors


def cleanup_old_news():
    try:
        cutoff = int((datetime.utcnow() - timedelta(days=7)).timestamp())
        # ← SỬA: delete() trả về số lượng, không phải result
        deleted_count = news_vectors.delete(where={"timestamp": {"$lt": cutoff}})
        print(f"[CLEANUP] Đã xóa {deleted_count} tin cũ (>7 ngày)")
    except Exception as e:
        print(f"[CLEANUP ERROR] {e}")


# Chạy mỗi ngày lúc 2:00 sáng
schedule.every().day.at("02:00").do(cleanup_old_news)

# Hoặc test ngay
if __name__ == "__main__":
    print("Test cleanup ngay...")
    cleanup_old_news()
