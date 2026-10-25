"""
News backend (FastAPI).

Setup:
    pip install fastapi uvicorn httpx python-dotenv

.env (same folder as this file):
    NEWS_API_KEY=your_newsapi_key_here

Run:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# NewsAPI has no built-in "politics", "weather" or "agriculture" categories,
# so each category is mapped to a search query instead.
CATEGORY_QUERIES = {
    "politics": "politics OR election OR parliament OR government",
    "weather": "weather OR forecast OR rainfall OR climate",
    "sports": "sports OR football OR athletics OR rugby",
    "agriculture": "agriculture OR farming OR crops OR livestock",
}

app = FastAPI(title="News Reader")


@app.get("/")
def index():
    """Serve the frontend so the browser and API share one origin (no CORS setup)."""
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/categories")
def categories():
    return list(CATEGORY_QUERIES.keys())


@app.get("/api/news")
async def get_news(
    category: str = Query("politics"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=30),
):
    if not NEWS_API_KEY:
        raise HTTPException(500, "NEWS_API_KEY is missing. Add it to your .env file.")

    query = CATEGORY_QUERIES.get(category)
    if query is None:
        raise HTTPException(400, f"Unknown category '{category}'.")

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "page": page,
        "pageSize": page_size,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Key goes in a header so it never appears in URLs or logs.
            resp = await client.get(NEWS_API_URL, params=params, headers={"X-Api-Key": NEWS_API_KEY})
    except httpx.RequestError:
        raise HTTPException(502, "Could not reach NewsAPI. Check your connection.")

    data = resp.json()
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, data.get("message", "NewsAPI returned an error."))

    # Send the browser only what it needs.
    articles = [
        {
            "title": a.get("title"),
            "description": a.get("description"),
            "url": a.get("url"),
            "image": a.get("urlToImage"),
            "source": (a.get("source") or {}).get("name"),
            "publishedAt": a.get("publishedAt"),
        }
        for a in data.get("articles", [])
        if a.get("title") and a["title"] != "[Removed]"
    ]

    return {"category": category, "total": data.get("totalResults", 0), "articles": articles}