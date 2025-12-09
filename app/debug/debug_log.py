# app/debug/debug_log.py
import time
from functools import wraps


def log_time(step_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            print(f"[TIMER] BẮT ĐẦU → {step_name}")
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                print(f"[TIMER] HOÀN TẤT → {step_name} | Thời gian: {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                print(
                    f"[TIMER] LỖI → {step_name} | Thời gian: {elapsed:.2f}s | Error: {e}"
                )
                raise

        return wrapper

    return decorator
