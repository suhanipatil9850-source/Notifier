# Web Scraper + Notifier – FastAPI
# Tracks a URL and notifies on content change
# Run: python main.py

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import requests
import hashlib

app = FastAPI()

# ---------- Database ----------
conn = sqlite3.connect("tracker.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS trackers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    url TEXT,
    last_hash TEXT
)
""")
conn.commit()

# ---------- Templates ----------
templates = Jinja2Templates(directory="templates")

# ---------- Helpers ----------
def get_page_hash(url: str) -> str:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return hashlib.sha256(r.text.encode()).hexdigest()

# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    cursor.execute("SELECT * FROM trackers")
    trackers = cursor.fetchall()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "trackers": trackers
    })

@app.post("/add")
def add_tracker(name: str = Form(...), url: str = Form(...)):
    page_hash = get_page_hash(url)
    cursor.execute(
        "INSERT INTO trackers (name, url, last_hash) VALUES (?, ?, ?)",
        (name, url, page_hash)
    )
    conn.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/check/{tid}")
def check_tracker(tid: int):
    cursor.execute("SELECT url, last_hash FROM trackers WHERE id=?", (tid,))
    url, last_hash = cursor.fetchone()
    new_hash = get_page_hash(url)

    if new_hash != last_hash:
        cursor.execute("UPDATE trackers SET last_hash=? WHERE id=?", (new_hash, tid))
        conn.commit()
        print(f"[ALERT] Change detected for {url}")

    return RedirectResponse("/", status_code=303)

@app.get("/delete/{tid}")
def delete_tracker(tid: int):
    cursor.execute("DELETE FROM trackers WHERE id=?", (tid,))
    conn.commit()
    return RedirectResponse("/", status_code=303)

# ---------- Run ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
