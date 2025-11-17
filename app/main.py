# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import dynamic_menu, semantic_search
from offline_scripts import newstrend_vectorizer
import schedule
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(semantic_search.router, prefix="/ai", tags=["Search"])
app.include_router(dynamic_menu.router, prefix="/ai", tags=["Recommendations"])
app.include_router(newstrend_vectorizer.router)  # THÊM DÒNG NÀY


@app.get("/")
def root():
    return {"status": "ok"}


def run_scheduler():
    from offline_scripts.cleanup_news import cleanup_old_news

    cleanup_old_news()
    while True:
        schedule.run_pending()
        time.sleep(3600)


threading.Thread(target=run_scheduler, daemon=True).start()
