"""Competitor Job Market Scraper (Prototype).

Extracts market listings from a public sandbox (quotes.toscrape.com)
simulating competitor hiring and skills monitoring for Nairobi HR managers.
"""

import argparse
import csv
from pathlib import Path
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
DEFAULT_OUTPUT = Path(__file__).parent / "job_listings.csv"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_page(url, retries=3, timeout=10):
    """Fetch an HTML page with automatic retries, exponential backoff, and UTF-8 encoding."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response
        except requests.RequestException as e:
            print(f"[!] Attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(2 * attempt)
    return None


def parse_page(html_text, base_url=BASE_URL):
    """Parse listing pods and extract at least four structured fields per item.

    Extracted fields:
      - text: Core description/listing text
      - author: Posting author / hiring company
      - tags: In-demand tags/skills (comma-separated)
      - tag_count: Number of tags/skills listed
      - author_url: Full URL to author/company profile page
    """
    soup = BeautifulSoup(html_text, "html.parser")
    records = []

    listing_nodes = soup.find_all("div", class_="quote")
    for node in listing_nodes:
        text_el = node.find("span", class_="text")
        author_el = node.find("small", class_="author")
        tags_els = node.find_all("a", class_="tag")
        link_el = node.find("a", href=True)

        text = text_el.get_text(strip=True) if text_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        tags = [tag.get_text(strip=True) for tag in tags_els]
        author_href = link_el["href"] if link_el else ""
        author_url = urljoin(base_url, author_href) if author_href else ""

        records.append({
            "text": text,
            "author": author,
            "tags": ", ".join(tags),
            "tag_count": len(tags),
            "author_url": author_url,
        })

    next_btn = soup.find("li", class_="next")
    next_url = None
    if next_btn and next_btn.find("a", href=True):
        next_url = urljoin(base_url, next_btn.find("a")["href"])

    return records, next_url


def scrape_listings(start_url=BASE_URL, max_pages=5, delay=1.0, output_file=DEFAULT_OUTPUT):
    """Crawl paginated listings up to max_pages and save them to CSV."""
    current_url = start_url
    all_records = []
    page_num = 1

    print(f"[*] Starting job market scrape from: {start_url}")
    print(f"[*] Target max pages: {max_pages} | Inter-request delay: {delay}s")

    while current_url and page_num <= max_pages:
        print(f"\n[*] Fetching Page {page_num}: {current_url}")
        resp = fetch_page(current_url)
        if not resp:
            print(f"[x] Skipping page {page_num} due to fetch failure.")
            break

        records, next_url = parse_page(resp.text, base_url=start_url)
        print(f"[+] Found {len(records)} listings on Page {page_num}")
        all_records.extend(records)

        current_url = next_url
        page_num += 1

        if current_url and page_num <= max_pages:
            time.sleep(delay)

    # Save records to CSV
    if all_records:
        fieldnames = ["text", "author", "tags", "tag_count", "author_url"]
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"\n[✓] Successfully scraped {len(all_records)} total listings across {page_num - 1} pages.")
        print(f"[✓] Saved data to: {output_path.resolve()}")
    else:
        print("\n[!] No listings collected.")

    return all_records


def main():
    parser = argparse.ArgumentParser(
        description="Scrape market listings for HR competitor intelligence."
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Maximum number of pages to scrape (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Polite delay between page requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.name})",
    )
    args = parser.parse_args()

    scrape_listings(max_pages=args.pages, delay=args.delay, output_file=args.output)


if __name__ == "__main__":
    main()
