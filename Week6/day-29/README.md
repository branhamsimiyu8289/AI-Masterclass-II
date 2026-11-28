# Day 29: Hardened Document Handler

## What Was Built

This project upgrades the [Day 26 Document Handler](../../day-26/document-handler/README.md) AI application into a tested, resilient, and observable CLI tool (`document_handler.py`) for processing business documents:

- **Invoice Preview (`preview_invoice`)**: Safely reads `supplier_invoice.pdf` and outputs page count and a 500-character preview.
- **AI Contract Analysis (`extract_contract_details`)**: Extracts party names, payment terms, delivery dates, and penalties from `supplier_contract.pdf` via the Google Gemini API.
- **Retry Logic with Exponential Backoff (`call_gemini_with_retry`)**: Retries transient failures (`429`, `500`, `502`, `503`, `504`, timeouts, and network errors) using exponential backoff (honoring numeric `Retry-After` headers when present) before falling back across the configured Gemini model list. Authentication errors (`401`/`403`) fail fast without wasted retries.
- **Structured Logging (`configure_logging`)**: Logs run lifecycle, PDF extraction summaries, retry attempts, model fallbacks, and errors to both stdout and `document_handler.log` without exposing `GEMINI_API_KEY`.
- **Word Sales Report (`create_monthly_sales_report`)**: Generates a formatted `.docx` report with dynamically computed revenue totals and period labels.
- **Batch Invoice Indexing (`index_invoices`)**: Scans the `invoices/` folder and writes a sorted `invoice_index.csv`.

## Bugs Fixed from Day 26

1. **Unhandled Gemini response crashes (`KeyError`/`IndexError`/`ValueError`)**: `extract_contract_details` previously indexed `data["candidates"][0]["content"]["parts"]` directly and did not catch invalid JSON or empty/blocked responses. Replaced with `_extract_gemini_text()` and safe JSON parsing.
2. **Word concatenation & empty-PDF API calls**: Pages were previously joined with `""` (merging the last word of one page into the first word of the next), and blank/scanned PDFs still triggered Gemini API requests. Pages are now joined with `"\n\n"` and empty contract PDFs fail early before calling Gemini.
3. **Invoice indexer fragility (`index_invoices`)**: Previously failed to match uppercase `.PDF` files, did not skip subdirectories named `*.pdf`, produced unsorted rows, left raw `\r` characters in CSV previews, and crashed the entire batch on a single corrupt or encrypted PDF.
4. **Corrupt/encrypted PDF & `.env` loading issues**: Added a shared `extract_pdf_text()` helper to catch `PdfReadError` and password-protected PDFs across all commands, and moved `.env` loading out of module import time into `load_api_key()`.
5. **Hardcoded report summary**: `create_monthly_sales_report()` previously hardcoded `"November 2024: KES 847,000"` instead of calculating the total from the report rows and `report_date`, and failed if parent directories did not exist.

## How to Run

From `Week6/day-29`:

1. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
2. Optional (required only when `supplier_contract.pdf` is present): copy `.env.example` to `.env` and set your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
3. Run the application:
   ```powershell
   python .\document_handler.py
   ```
   Optional flags:
   ```powershell
   python .\document_handler.py --help
   python .\document_handler.py --contract path\to\contract.pdf --max-retries 3 --log-level INFO
   ```
4. Run the unit test suite (uses mocked HTTP responses; no API key required):
   ```powershell
   python -m unittest discover -v
   ```
