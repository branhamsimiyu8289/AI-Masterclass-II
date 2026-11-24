# Document Handler

Run the script to perform the document tasks in sequence:

- Print a text preview of `supplier_invoice.pdf`, if present.
- Extract key contract details from `supplier_contract.pdf` using Gemini, if
  present.
- Create `november_report.docx`.
- Index PDFs in the `invoices` folder into `invoice_index.csv`, if the folder is
  present.

## Setup

From this directory, install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

If `supplier_contract.pdf` is present, set `GEMINI_API_KEY` in your environment
or in a `.env` file in the current directory:

```env
GEMINI_API_KEY=your_api_key_here
```

## Run

Place the invoice and contract PDFs, and optionally an `invoices` folder, in
the current directory. Then run:

```powershell
python .\document-handler.py
```

Contract analysis tries the configured Gemini model list in order. The API key
is required only when `supplier_contract.pdf` is present.
