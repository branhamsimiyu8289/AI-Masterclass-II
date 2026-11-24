# Document Handler

The script provides separate commands for each document task:

- Extract a text preview from a PDF.
- Ask Gemini to extract key terms from a contract PDF.
- Create an example sales report in Word format.
- Index PDFs in a folder into a CSV file.

## Setup

From this directory, install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

For contract analysis, set `GEMINI_API_KEY` in your environment or create a
`.env` file in this directory:

```env
GEMINI_API_KEY=your_api_key_here
```

## Usage

Run these commands from this directory:

```powershell
python .\document-handler.py extract .\supplier_invoice.pdf
python .\document-handler.py analyze-contract .\supplier_contract.pdf
python .\document-handler.py create-report --output .\november_report.docx
python .\document-handler.py index-invoices .\invoices --output .\invoice_index.csv
```

The contract-analysis command accepts `--model` (or `GEMINI_MODEL` in `.env`) to
select a Gemini model (defaults to `gemini-flash-lite-latest`).
The invoice index defaults to the `invoices` folder and writes
`invoice_index.csv` in the current directory if paths are omitted.
