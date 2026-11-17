import csv
from pathlib import Path
import time
import requests
from bs4 import BeautifulSoup

URL = "https://books.toscrape.com/"
CSV_PATH = Path(__file__).parent / "books.csv"


def fetch_page(url, retries=3):
    """Fetch a web page with retry logic and timeout."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    return None


def scrape_books(url=URL, output_file=CSV_PATH):
    """Scrape book titles, prices, and ratings from the page and export to CSV."""
    response = fetch_page(url)
    if not response:
        print("Failed to fetch page.")
        return []

    print("Status:", response.status_code)
    print("Page size:", len(response.text), "characters")

    soup = BeautifulSoup(response.text, "html.parser")
    books = soup.find_all("article", class_="product_pod")
    print(f"Found {len(books)} books on this page")

    # Preview the first 5 books
    for book in books[:5]:
        title = book.find("h3").find("a")["title"]
        price = book.find("p", class_="price_color").text
        print(f"{title}: {price}")

    # Extract all book data
    books_data = []
    for book in books:
        title = book.find("h3").find("a")["title"]
        price = book.find("p", class_="price_color").text
        rating = book.find("p", class_="star-rating")["class"][1]
        books_data.append({"title": title, "price": price, "rating": rating})

    # Save to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price", "rating"])
        writer.writeheader()
        writer.writerows(books_data)

    print(f"Saved {len(books_data)} books to {Path(output_file).name}")
    return books_data


if __name__ == "__main__":
    scrape_books()
