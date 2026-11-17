# Day 22: Books to Scrape Web Scraper

A lightweight, resilient Python web scraper that extracts book data from [Books to Scrape](https://books.toscrape.com/) and exports it to a structured CSV file.

## Features

- **Resilient HTTP Requests**: Includes a retry mechanism (`fetch_page`) with timeout and automatic error handling.
- **HTML Parsing**: Uses BeautifulSoup to locate book cards (`article.product_pod`) and extract book details.
- **Terminal Preview**: Prints page status, page size, total books found, and a preview of the first 5 books.
- **CSV Export**: Saves all extracted books (`title`, `price`, and `rating`) into `books.csv` with UTF-8 encoding.

## Project Structure

```text
web-scraper/
├── books.csv           # Generated CSV output containing scraped book records
├── requirements.txt    # Project dependencies (requests, beautifulsoup4)
├── scraper.py          # Main scraper script
└── README.md           # Project documentation
```

## Setup & Usage

### 1. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Run the Scraper

```bash
python scraper.py
```

### 3. Example Terminal Output

```text
Status: 200
Page size: 51274 characters
Found 20 books on this page
A Light in the Attic: £51.77
Tipping the Velvet: £53.74
Soumission: £50.10
Sharp Objects: £47.82
Sapiens: A Brief History of Humankind: £54.23
Saved 20 books to books.csv
```

### 4. Sample CSV Data (`books.csv`)

| title | price | rating |
|---|---|---|
| A Light in the Attic | £51.77 | Three |
| Tipping the Velvet | £53.74 | One |
| Soumission | £50.10 | One |
| Sharp Objects | £47.82 | Four |
| Sapiens: A Brief History of Humankind | £54.23 | Five |
