import csv
import os
from datetime import date
from pathlib import Path

import httpx
from docx import Document
from dotenv import find_dotenv, load_dotenv
from pypdf import PdfReader

load_dotenv(find_dotenv(usecwd=True))

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]


def preview_invoice(pdf_path: str = "supplier_invoice.pdf") -> None:
    """Read a PDF invoice and print page count and a text preview."""
    if not Path(pdf_path).is_file():
        print(f"Skipping preview: '{pdf_path}' not found.")
        return

    reader = PdfReader(pdf_path)
    print(f"Pages: {len(reader.pages)}")

    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"

    print(full_text[:500])


def extract_contract_details(pdf_path: str = "supplier_contract.pdf") -> None:
    """Extract key contract terms from a PDF using the Gemini API."""
    if not Path(pdf_path).is_file():
        print(f"Skipping contract extraction: '{pdf_path}' not found.")
        return

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to your .env file or environment."
        )

    reader = PdfReader(pdf_path)
    doc_text = "".join((page.extract_text() or "") for page in reader.pages)

    prompt = (
        "From this contract, extract: party names, payment terms, "
        "delivery date, and any penalties.\n\n"
        f"Document:\n\n{doc_text[:3000]}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048},
    }

    last_error = "Unknown error"
    with httpx.Client(timeout=30.0) as client:
        for model_name in GEMINI_MODELS:
            url = f"{GEMINI_API_BASE}/{model_name}:generateContent"
            try:
                response = client.post(
                    url,
                    headers={"x-goog-api-key": api_key},
                    json=payload,
                )
            except httpx.HTTPError as exc:
                last_error = f"{model_name}: {exc}"
                continue

            if response.status_code == 200:
                data = response.json()
                parts = data["candidates"][0]["content"]["parts"]
                answer = "\n".join(
                    p.get("text", "")
                    for p in parts
                    if p.get("text") and not p.get("thought")
                ).strip()
                print(answer)
                return

            if response.status_code in (401, 403):
                raise RuntimeError("Gemini API authentication failed. Check GEMINI_API_KEY.")

            last_error = f"HTTP {response.status_code} ({model_name})"

    raise RuntimeError(f"All Gemini models failed: {last_error}")


def create_monthly_sales_report(output_path: str = "november_report.docx") -> None:
    """Generate a formatted Word sales report."""
    doc = Document()
    doc.add_heading("Monthly Sales Report", 0)

    p = doc.add_paragraph()
    p.add_run(f"Prepared by: Kamau Stores | Date: {date.today()}")

    doc.add_heading("Summary", level=1)
    doc.add_paragraph("Total sales for November 2024: KES 847,000. Up 12% from October.")

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Product", "Units", "Revenue (KES)"

    data = [
        ("Maize flour", 420, 336000),
        ("Rice", 180, 324000),
        ("Cooking oil", 210, 187000),
    ]
    for row in data:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)

    doc.save(output_path)
    print(f"Report saved: {output_path}")


def index_invoices(
    pdf_folder: str = "invoices",
    output_csv: str = "invoice_index.csv",
) -> None:
    """Index all PDF files in a folder and save a summary CSV."""
    if not os.path.isdir(pdf_folder):
        print(f"Skipping invoice index: folder '{pdf_folder}' not found.")
        return

    results = []
    for fname in os.listdir(pdf_folder):
        if not fname.endswith(".pdf"):
            continue
        path = os.path.join(pdf_folder, fname)
        reader = PdfReader(path)
        text = "".join((p.extract_text() or "") for p in reader.pages)
        results.append(
            {
                "file": fname,
                "pages": len(reader.pages),
                "chars": len(text),
                "preview": text[:100].replace("\n", " "),
            }
        )

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "pages", "chars", "preview"])
        writer.writeheader()
        writer.writerows(results)
    print(f"Indexed {len(results)} invoices")


if __name__ == "__main__":
    preview_invoice()
    extract_contract_details()
    create_monthly_sales_report()
    index_invoices()
