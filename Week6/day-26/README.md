# PDF Q&A Assistant (Gemini API)

A Python CLI script (`pdf_qa.py`) that extracts text from any user-provided PDF document and answers questions grounded strictly in its contents using the Google Gemini API.

## What Was Built

- **PDF text extraction (`pypdf`)**: Reads multi-page PDFs with `[Page N]` markers so answers can cite exact page numbers.
- **Scanned PDF fallback**: If a PDF has no embedded text (e.g., scanned pages), the script sends the PDF bytes directly to Gemini via `inline_data` (up to 15 MB).
- **Large-document handling**: Documents exceeding 120,000 characters automatically select page 1 plus the highest keyword-matching pages for the question.
- **Interactive & one-shot CLI modes**:
  - Interactive mode remembers recent Q&A history in the session for follow-up questions.
  - One-shot mode (`-q`) answers a single question and exits.
- **Gemini API integration (`httpx`)**: Calls the Gemini `generateContent` endpoint with `gemini-flash-lite-latest` (falling back to `gemini-flash-latest`, `gemini-3.1-flash-lite-preview`, and `gemini-3-flash-preview` if busy).

## Requirements

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- Packages in `requirements.txt` (`httpx`, `pypdf`, `python-dotenv`)

## Setup

1. Install dependencies (if not already installed):

   ```powershell
   pip install -r requirements.txt
   ```

2. Create a `.env` file in this folder from `.env.example` and add your key:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edit `.env`:

   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## How to Run

From `Week6\day-26`:

- **Interactive mode (prompts for PDF path, then lets you ask multiple questions):**

  ```powershell
  python pdf_qa.py
  ```

- **Interactive mode with a PDF path argument:**

  ```powershell
  python pdf_qa.py path\to\document.pdf
  ```

- **One-shot question:**

  ```powershell
  python pdf_qa.py path\to\document.pdf -q "What are the payment terms?"
  ```

- **Optional model override:**

  ```powershell
  python pdf_qa.py path\to\document.pdf -q "Summarize this document" -m gemini-flash-latest
  ```

## Run Unit Tests

```powershell
python -m unittest -v test_pdf_qa.py
```
