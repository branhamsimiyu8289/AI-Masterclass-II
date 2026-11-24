from pypdf import PdfReader

reader = PdfReader("supplier_invoice.pdf")

print(f"Pages: {len(reader.pages)}")

# Extract all text from all pages
full_text = ""
for page in reader.pages:
    full_text += page.extract_text() + "
"

print(full_text[:500])  # first 500 characters

from pypdf import PdfReader
import anthropic, os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Extract the text
reader = PdfReader("supplier_contract.pdf")
doc_text = "".join(page.extract_text() for page in reader.pages)

# Ask AI to extract key details
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": f"From this contract, extract: party names, payment terms, delivery date, and any penalties. Document:

{doc_text[:3000]}"
    }]
)
print(response.content[0].text)

from docx import Document
from docx.shared import Pt, RGBColor
from datetime import date

doc = Document()
doc.add_heading("Monthly Sales Report", 0)

# Add metadata paragraph
p = doc.add_paragraph()
p.add_run(f"Prepared by: Kamau Stores | Date: {date.today()}")

# Add a section heading
doc.add_heading("Summary", level=1)
doc.add_paragraph("Total sales for November 2024: KES 847,000. Up 12% from October.")

# Add a table
table = doc.add_table(rows=1, cols=3)
table.style = "Table Grid"
hdr = table.rows[0].cells
hdr[0].text, hdr[1].text, hdr[2].text = "Product", "Units", "Revenue (KES)"

data = [("Maize flour", 420, 336000), ("Rice", 180, 324000), ("Cooking oil", 210, 187000)]
for row in data:
    cells = table.add_row().cells
    for i, val in enumerate(row):
        cells[i].text = str(val)

doc.save("november_report.docx")
print("Report saved: november_report.docx")

import os, csv
from pypdf import PdfReader

PDF_FOLDER = "invoices"
results = []

for fname in os.listdir(PDF_FOLDER):
    if not fname.endswith(".pdf"):
        continue
    path = os.path.join(PDF_FOLDER, fname)
    reader = PdfReader(path)
    text = "".join(p.extract_text() for p in reader.pages)
    results.append({
        "file": fname,
        "pages": len(reader.pages),
        "chars": len(text),
        "preview": text[:100].replace("
", " ")
    })

with open("invoice_index.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["file", "pages", "chars", "preview"])
    writer.writeheader()
    writer.writerows(results)
print(f"Indexed {len(results)} invoices")