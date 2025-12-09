# offline_scripts/update_user_similarity.py
import schedule
import threading
import time
import os
from datetime import datetime

# CÁCH IMPORT CHẮC CHẮN NHẤT: dùng importlib
import importlib.util
import sys

# Đường dẫn tuyệt đối đến file create_user_similarity.py
FILE_PATH = os.path.join(os.path.dirname(__file__), "create_user_similarity.py")

spec = importlib.util.spec_from_file_location("create_user_similarity", FILE_PATH)
create_sim = importlib.util.module_from_spec(spec)
sys.modules["create_user_similarity"] = create_sim
spec.loader.exec_module(create_sim)

# Bây giờ mới gọi hàm main
rebuild_user_similarity = create_sim.main

SIM_FILE = os.path.join(os.path.dirname(__file__), "data", "user_similarity.json")

def update_user_similarity_job():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Bắt đầu cập nhật user_similarity...")
    
    # Xóa file cũ nếu có
    if os.path.exists(SIM_FILE):
        try:
            os.remove(SIM_FILE)
            print(f"[UPDATE] Đã xóa file cũ")
        except:
            pass
    
    # Tính lại
    try:
        rebuild_user_similarity()
        print(f"[UPDATE] Hoàn tất! File đã được tạo lại")
    except Exception as e:
        print(f"[UPDATE ERROR] {e}")

# CHẠY NGAY KHI KHỞI ĐỘNG
print("[INIT] Đang tạo user_similarity.json lần đầu...")
update_user_similarity_job()

# LÊN LỊCH CHẠY MỖI NGÀY 3H SÁNG
schedule.every().day.at("03:00").do(update_user_similarity_job)
print("[SCHEDULE] Đã lên lịch tự động cập nhật user_similarity mỗi ngày 3h sáng")

if __name__ == "__main__":
    update_user_similarity_job()