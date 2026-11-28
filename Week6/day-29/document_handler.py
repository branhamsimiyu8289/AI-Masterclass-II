"""
Document Handler (Hardened AI Application)
------------------------------------------
Extracts text from PDF invoices, analyzes contract terms using the Google Gemini
API (with exponential-backoff retries, model fallback, and structured logging),
generates formatted Word sales reports, and indexes invoice PDFs to CSV.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Sequence

import httpx
from dotenv import find_dotenv, load_dotenv
from docx import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS: tuple[str, ...] = (
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
AUTH_STATUS_CODES = frozenset({401, 403})
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_CONTRACT_CHARS = 12_000

DEFAULT_SALES_ROWS: list[tuple[str, int, int]] = [
    ("Maize flour", 420, 336000),
    ("Rice", 180, 324000),
    ("Cooking oil", 210, 187000),
]

logger = logging.getLogger("document_handler")


class GeminiAuthError(RuntimeError):
    """Raised when the Gemini API rejects authentication (HTTP 401/403)."""


@dataclass
class PdfExtractionResult:
    """Extracted text and metadata from a PDF file."""

    path: Path
    page_count: int
    text: str


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = "document_handler.log",
) -> logging.Logger:
    """Configure console and optional file logging without duplicating handlers."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    logger.setLevel(numeric_level)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def load_api_key() -> str:
    """Load GEMINI_API_KEY from script-local .env, CWD .env, or environment."""
    script_env = Path(__file__).resolve().parent / ".env"
    if script_env.is_file():
        load_dotenv(script_env, override=False)

    found_env = find_dotenv(usecwd=True)
    if found_env:
        load_dotenv(found_env, override=False)

    return os.getenv("GEMINI_API_KEY", "").strip()


def extract_pdf_text(pdf_path: str | Path) -> PdfExtractionResult:
    """
    Safely read a PDF file and return page-separated extracted text.

    Raises FileNotFoundError if missing, or ValueError if unreadable/encrypted.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: '{path}'")
    if not path.is_file():
        raise ValueError(f"Path is not a file: '{path}'")

    try:
        reader = PdfReader(str(path))
    except PdfReadError as exc:
        raise ValueError(f"Corrupt or unreadable PDF '{path.name}': {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to open PDF '{path.name}': {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("")
        except Exception as exc:
            raise ValueError(f"PDF '{path.name}' is password-protected.") from exc
        if not decrypted:
            raise ValueError(f"PDF '{path.name}' is password-protected.")

    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception as exc:
            raise ValueError(
                f"Failed to extract text from page {index} of '{path.name}': {exc}"
            ) from exc
        if text:
            page_texts.append(text)

    combined_text = "\n\n".join(page_texts)
    return PdfExtractionResult(
        path=path,
        page_count=len(reader.pages),
        text=combined_text,
    )


def _extract_gemini_text(data: Any) -> str:
    """Safely extract non-thought text from a Gemini generateContent JSON payload."""
    if not isinstance(data, dict):
        return ""
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""

    text_parts = [
        p.get("text", "")
        for p in parts
        if isinstance(p, dict) and p.get("text") and not p.get("thought")
    ]
    return "\n".join(text_parts).strip()


def _parse_retry_after(headers: httpx.Headers | dict[str, str] | None) -> float | None:
    """Parse numeric Retry-After header seconds when present."""
    if not headers:
        return None
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    try:
        seconds = float(raw)
        return max(0.0, seconds)
    except (TypeError, ValueError):
        return None


def preview_invoice(pdf_path: str | Path = "supplier_invoice.pdf") -> str | None:
    """Read a PDF invoice, log summary metadata, and print a 500-char preview."""
    path = Path(pdf_path)
    if not path.is_file():
        logger.info("Skipping preview: '%s' not found.", path)
        print(f"Skipping preview: '{path}' not found.")
        return None

    result = extract_pdf_text(path)
    preview = result.text[:500]
    logger.info(
        "Previewed invoice '%s' (%d pages, %d chars).",
        path.name,
        result.page_count,
        len(result.text),
    )
    print(f"Pages: {result.page_count}")
    print(preview)
    return preview


def call_gemini_with_retry(
    prompt: str,
    api_key: str,
    models: Sequence[str] = GEMINI_MODELS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
    client: httpx.Client | None = None,
) -> tuple[str, str]:
    """
    Call Gemini generateContent across candidate models with exponential-backoff retries.

    Retries transient HTTP status codes (429, 500, 502, 503, 504), timeouts, and
    network errors. Does not retry auth failures (401/403) or bad requests (400).
    Returns (response_text, model_used).
    """
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to your .env file or environment."
        )
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1.")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048},
    }

    owns_client = client is None
    active_client = client or httpx.Client(timeout=timeout)
    last_error = "Unknown error"

    try:
        for model_name in models:
            url = f"{GEMINI_API_BASE}/{model_name}:generateContent"
            for attempt in range(1, max_retries + 1):
                logger.info(
                    "Calling Gemini model '%s' (attempt %d/%d).",
                    model_name,
                    attempt,
                    max_retries,
                )
                try:
                    response = active_client.post(
                        url,
                        headers={"x-goog-api-key": api_key.strip()},
                        json=payload,
                    )
                except httpx.TimeoutException as exc:
                    last_error = f"{model_name}: request timed out ({exc})"
                    logger.warning(
                        "Timeout calling '%s' on attempt %d/%d.",
                        model_name,
                        attempt,
                        max_retries,
                    )
                except httpx.RequestError as exc:
                    last_error = f"{model_name}: network error ({exc})"
                    logger.warning(
                        "Network error calling '%s' on attempt %d/%d: %s",
                        model_name,
                        attempt,
                        max_retries,
                        exc,
                    )
                else:
                    status = response.status_code
                    if status in AUTH_STATUS_CODES:
                        logger.error(
                            "Gemini authentication failed with HTTP %d on '%s'.",
                            status,
                            model_name,
                        )
                        raise GeminiAuthError(
                            "Gemini API authentication failed. Check GEMINI_API_KEY."
                        )

                    if status == 200:
                        try:
                            data = response.json()
                        except ValueError as exc:
                            last_error = f"{model_name}: invalid JSON response ({exc})"
                            logger.warning(
                                "Invalid JSON from '%s' on attempt %d/%d.",
                                model_name,
                                attempt,
                                max_retries,
                            )
                        else:
                            answer = _extract_gemini_text(data)
                            if answer:
                                logger.info(
                                    "Received response from '%s' (%d chars).",
                                    model_name,
                                    len(answer),
                                )
                                return answer, model_name
                            last_error = f"{model_name}: empty or blocked response"
                            logger.warning(
                                "Empty or blocked response from '%s' on attempt %d/%d.",
                                model_name,
                                attempt,
                                max_retries,
                            )
                    elif status in RETRYABLE_STATUS_CODES:
                        last_error = f"HTTP {status} ({model_name})"
                        logger.warning(
                            "Retryable HTTP %d from '%s' on attempt %d/%d.",
                            status,
                            model_name,
                            attempt,
                            max_retries,
                        )
                        if attempt < max_retries:
                            retry_after = _parse_retry_after(response.headers)
                            delay = (
                                retry_after
                                if retry_after is not None
                                else base_delay * (2 ** (attempt - 1))
                            )
                            logger.info("Backing off %.2fs before retry.", delay)
                            sleep_fn(delay)
                            continue
                        break
                    else:
                        last_error = f"HTTP {status} ({model_name})"
                        logger.warning(
                            "Non-retryable HTTP %d from '%s'; falling back to next model.",
                            status,
                            model_name,
                        )
                        break

                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info("Backing off %.2fs before retry.", delay)
                    sleep_fn(delay)
    finally:
        if owns_client:
            active_client.close()

    logger.error("All Gemini models failed: %s", last_error)
    raise RuntimeError(f"All Gemini models failed: {last_error}")


def extract_contract_details(
    pdf_path: str | Path = "supplier_contract.pdf",
    api_key: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    sleep_fn: Callable[[float], None] = time.sleep,
    client: httpx.Client | None = None,
) -> str | None:
    """Extract key contract terms from a PDF using the Gemini API."""
    path = Path(pdf_path)
    if not path.is_file():
        logger.info("Skipping contract extraction: '%s' not found.", path)
        print(f"Skipping contract extraction: '{path}' not found.")
        return None

    extraction = extract_pdf_text(path)
    if not extraction.text.strip():
        raise ValueError(
            f"Contract PDF '{path.name}' contains no extractable text (it may be scanned)."
        )

    resolved_key = api_key if api_key is not None else load_api_key()
    prompt = (
        "From this contract, extract: party names, payment terms, "
        "delivery date, and any penalties.\n\n"
        f"Document:\n\n{extraction.text[:MAX_CONTRACT_CHARS]}"
    )

    answer, model_used = call_gemini_with_retry(
        prompt=prompt,
        api_key=resolved_key,
        max_retries=max_retries,
        base_delay=base_delay,
        sleep_fn=sleep_fn,
        client=client,
    )
    logger.info("Extracted contract details from '%s' using '%s'.", path.name, model_used)
    print(answer)
    return answer


def create_monthly_sales_report(
    output_path: str | Path = "monthly_sales_report.docx",
    rows: Sequence[tuple[str, int, int]] | None = None,
    report_date: date | None = None,
    business_name: str = "Kamau Stores",
    growth_note: str = "Up 12% from previous month.",
) -> Path:
    """Generate a formatted Word sales report with dynamically calculated totals."""
    active_rows = list(rows) if rows is not None else list(DEFAULT_SALES_ROWS)
    active_date = report_date or date.today()
    total_revenue = sum(revenue for _, _, revenue in active_rows)
    period_label = active_date.strftime("%B %Y")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    doc.add_heading("Monthly Sales Report", 0)

    p = doc.add_paragraph()
    p.add_run(f"Prepared by: {business_name} | Date: {active_date.isoformat()}")

    doc.add_heading("Summary", level=1)
    summary_text = f"Total sales for {period_label}: KES {total_revenue:,}."
    if growth_note:
        summary_text = f"{summary_text} {growth_note}"
    doc.add_paragraph(summary_text)

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Product", "Units", "Revenue (KES)"

    for row in active_rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)

    doc.save(str(destination))
    logger.info(
        "Saved monthly sales report to '%s' (%d products, KES %s).",
        destination,
        len(active_rows),
        f"{total_revenue:,}",
    )
    print(f"Report saved: {destination}")
    return destination


def _clean_preview(text: str, limit: int = 100) -> str:
    """Collapse newlines and excessive whitespace into a clean single-line preview."""
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed[:limit]


def index_invoices(
    pdf_folder: str | Path = "invoices",
    output_csv: str | Path = "invoice_index.csv",
) -> list[dict[str, object]]:
    """Index all PDF files in a folder and save a sorted summary CSV."""
    folder = Path(pdf_folder)
    if not folder.is_dir():
        logger.info("Skipping invoice index: folder '%s' not found.", folder)
        print(f"Skipping invoice index: folder '{folder}' not found.")
        return []

    pdf_files = sorted(
        (
            entry
            for entry in folder.iterdir()
            if entry.is_file() and entry.suffix.lower() == ".pdf"
        ),
        key=lambda p: p.name.casefold(),
    )

    results: list[dict[str, object]] = []
    for path in pdf_files:
        try:
            extraction = extract_pdf_text(path)
        except ValueError as exc:
            logger.warning("Skipping unreadable invoice '%s': %s", path.name, exc)
            results.append(
                {
                    "file": path.name,
                    "pages": 0,
                    "chars": 0,
                    "status": "error",
                    "preview": str(exc)[:100],
                }
            )
            continue

        results.append(
            {
                "file": path.name,
                "pages": extraction.page_count,
                "chars": len(extraction.text),
                "status": "ok" if extraction.text.strip() else "empty",
                "preview": _clean_preview(extraction.text, limit=100),
            }
        )

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["file", "pages", "chars", "status", "preview"]
        )
        writer.writeheader()
        writer.writerows(results)

    logger.info("Indexed %d invoice files into '%s'.", len(results), csv_path)
    print(f"Indexed {len(results)} invoices")
    return results


def build_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Process supplier invoices, extract contract terms with Gemini, and generate sales reports."
    )
    parser.add_argument(
        "--invoice",
        default="supplier_invoice.pdf",
        help="Path to supplier invoice PDF to preview (default: supplier_invoice.pdf)",
    )
    parser.add_argument(
        "--contract",
        default="supplier_contract.pdf",
        help="Path to supplier contract PDF for Gemini analysis (default: supplier_contract.pdf)",
    )
    parser.add_argument(
        "--report",
        default="monthly_sales_report.docx",
        help="Output path for Word sales report (default: monthly_sales_report.docx)",
    )
    parser.add_argument(
        "--invoices-dir",
        default="invoices",
        help="Folder of PDF invoices to index (default: invoices)",
    )
    parser.add_argument(
        "--index-csv",
        default="invoice_index.csv",
        help="Output CSV path for invoice index (default: invoice_index.csv)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Max retry attempts per Gemini model on transient errors (default: {DEFAULT_MAX_RETRIES})",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        default="document_handler.log",
        help="Log file path (default: document_handler.log)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)
    logger.info("Starting document handler run.")

    exit_code = 0
    try:
        preview_invoice(args.invoice)
    except ValueError as exc:
        logger.error("Invoice preview failed: %s", exc)
        print(f"Error previewing invoice: {exc}", file=sys.stderr)
        exit_code = 1

    try:
        extract_contract_details(
            args.contract,
            max_retries=args.max_retries,
        )
    except (ValueError, RuntimeError) as exc:
        logger.error("Contract extraction failed: %s", exc)
        print(f"Error extracting contract details: {exc}", file=sys.stderr)
        exit_code = 1

    create_monthly_sales_report(args.report)
    index_invoices(args.invoices_dir, args.index_csv)
    logger.info("Document handler finished with exit code %d.", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
