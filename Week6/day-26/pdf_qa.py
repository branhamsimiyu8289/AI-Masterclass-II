"""
PDF Question & Answer Script (Gemini API)
-----------------------------------------
Extracts text from a user-provided PDF document and answers questions grounded
strictly in the document's contents using the Google Gemini API.

Usage:
    python pdf_qa.py
    python pdf_qa.py path/to/document.pdf
    python pdf_qa.py path/to/document.pdf -q "What are the payment terms?"
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import httpx
from dotenv import find_dotenv, load_dotenv
from pypdf import PdfReader
from pypdf.errors import PdfReadError

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]
MAX_CONTEXT_CHARS = 120_000
MAX_INLINE_PDF_BYTES = 15 * 1024 * 1024  # 15 MB limit for scanned-PDF fallback
REQUEST_TIMEOUT_SECONDS = 45.0

SYSTEM_INSTRUCTION = """You are a precise document assistant that answers questions strictly based on the provided PDF document.

Rules:
1. Answer ONLY using facts present in the provided PDF document.
2. Cite page numbers (e.g., [Page 2]) whenever possible so the user can verify the source.
3. If the answer is not stated or cannot be reliably determined from the document, say clearly: "The provided PDF does not contain enough information to answer that."
4. Keep answers clear, direct, and concise. Use bullet points when listing multiple items."""

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
    "from", "how", "in", "is", "it", "of", "on", "or", "that", "the",
    "their", "there", "these", "this", "to", "was", "were", "what", "when",
    "where", "which", "who", "why", "will", "with",
}


@dataclass
class PdfDocument:
    """Represents extracted page text and metadata for a PDF file."""

    path: Path
    pages: list[tuple[int, str]]
    file_size_bytes: int

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def total_chars(self) -> int:
        return sum(len(text) for _, text in self.pages)

    @property
    def has_text(self) -> bool:
        return any(text.strip() for _, text in self.pages)


def load_api_key() -> str:
    """Load GEMINI_API_KEY from environment or nearby .env files."""
    script_env = Path(__file__).resolve().parent / ".env"
    if script_env.is_file():
        load_dotenv(script_env, override=False)

    found_env = find_dotenv(usecwd=True)
    if found_env:
        load_dotenv(found_env, override=False)

    return os.getenv("GEMINI_API_KEY", "").strip()


def clean_user_path(raw_path: str) -> Path:
    """Strip whitespace and surrounding quotes (common with Windows Copy as path)."""
    cleaned = raw_path.strip()
    if len(cleaned) >= 2 and (
        (cleaned[0] == '"' and cleaned[-1] == '"')
        or (cleaned[0] == "'" and cleaned[-1] == "'")
    ):
        cleaned = cleaned[1:-1].strip()
    return Path(cleaned).expanduser()


def extract_pdf(pdf_path: Path) -> PdfDocument:
    """Validate and extract per-page text from a PDF file."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path.name}")

    try:
        reader = PdfReader(str(pdf_path))
    except PdfReadError as exc:
        raise ValueError(f"Could not read PDF '{pdf_path.name}': {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to open PDF '{pdf_path.name}': {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("")
        except Exception as exc:
            raise ValueError(f"PDF '{pdf_path.name}' is password-protected.") from exc
        if not decrypted:
            raise ValueError(f"PDF '{pdf_path.name}' is password-protected.")

    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        pages.append((index, text))

    return PdfDocument(
        path=pdf_path,
        pages=pages,
        file_size_bytes=pdf_path.stat().st_size,
    )


def select_relevant_pages(
    doc: PdfDocument,
    question: str,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> tuple[str, bool]:
    """
    Format page-tagged document text for the prompt.
    If the document exceeds max_chars, select page 1 plus the highest-scoring
    pages for the question so the prompt fits comfortably within limits.
    """
    formatted_pages = [
        f"[Page {page_num}]\n{text}"
        for page_num, text in doc.pages
        if text.strip()
    ]
    full_context = "\n\n".join(formatted_pages)
    if len(full_context) <= max_chars:
        return full_context, False

    keywords = {
        word
        for word in re.findall(r"[a-z0-9]+", question.lower())
        if len(word) > 2 and word not in STOP_WORDS
    }

    scored_pages: list[tuple[int, int, str]] = []
    for page_num, text in doc.pages:
        if not text.strip():
            continue
        text_lower = text.lower()
        score = sum(text_lower.count(kw) for kw in keywords) if keywords else 0
        if page_num == 1:
            score += 1  # Keep title/overview page when possible
        scored_pages.append((score, page_num, f"[Page {page_num}]\n{text}"))

    # Prioritize higher keyword matches, preserving earlier pages on ties
    scored_pages.sort(key=lambda item: (-item[0], item[1]))

    selected: list[tuple[int, str]] = []
    used_chars = 0
    for _, page_num, block in scored_pages:
        block_len = len(block) + 2
        if selected and used_chars + block_len > max_chars:
            continue
        selected.append((page_num, block))
        used_chars += block_len

    # Re-order selected pages chronologically for coherent reading
    selected.sort(key=lambda item: item[0])
    truncated_context = "\n\n".join(block for _, block in selected)
    if len(truncated_context) > max_chars:
        truncated_context = truncated_context[:max_chars]

    return truncated_context, True


def build_contents(
    doc: PdfDocument,
    question: str,
    history: Sequence[tuple[str, str]] = (),
) -> tuple[list[dict], bool]:
    """Build Gemini API contents payload using extracted text or inline PDF fallback."""
    contents: list[dict] = []

    if doc.has_text:
        context_text, was_truncated = select_relevant_pages(doc, question)
        doc_part = {
            "text": (
                f"PDF Filename: {doc.path.name}\n"
                f"Total Pages: {doc.page_count}\n\n"
                f"--- BEGIN PDF CONTENT ---\n{context_text}\n--- END PDF CONTENT ---"
            )
        }
    else:
        if doc.file_size_bytes > MAX_INLINE_PDF_BYTES:
            raise ValueError(
                "This PDF has no extractable text (likely scanned images) and exceeds "
                f"the {MAX_INLINE_PDF_BYTES // (1024 * 1024)} MB inline upload limit."
            )
        encoded_pdf = base64.b64encode(doc.path.read_bytes()).decode("ascii")
        doc_part = {
            "inline_data": {
                "mime_type": "application/pdf",
                "data": encoded_pdf,
            }
        }
        was_truncated = False

    if not history:
        contents.append(
            {
                "role": "user",
                "parts": [doc_part, {"text": f"Question: {question}"}],
            }
        )
        return contents, was_truncated

    # Include the document in the first user turn, then append prior Q&A turns
    first_q, first_a = history[0]
    contents.append(
        {"role": "user", "parts": [doc_part, {"text": f"Question: {first_q}"}]}
    )
    contents.append({"role": "model", "parts": [{"text": first_a}]})

    for prev_q, prev_a in history[1:]:
        contents.append({"role": "user", "parts": [{"text": f"Question: {prev_q}"}]})
        contents.append({"role": "model", "parts": [{"text": prev_a}]})

    contents.append({"role": "user", "parts": [{"text": f"Question: {question}"}]})
    return contents, was_truncated


def ask_gemini(
    doc: PdfDocument,
    question: str,
    api_key: str,
    models: Sequence[str] | None = None,
    history: Sequence[tuple[str, str]] = (),
    http_client: httpx.Client | None = None,
) -> tuple[str, str, bool]:
    """
    Send the PDF document and question to the Gemini generateContent API.
    Returns (answer_text, model_used, was_truncated).
    """
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. Set it in a .env file or environment variable."
        )

    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question cannot be empty.")

    model_candidates = list(models) if models else list(DEFAULT_MODELS)
    contents, was_truncated = build_contents(doc, cleaned_question, history=history)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
    last_error = "Unknown error"

    try:
        for model_name in model_candidates:
            url = f"{GEMINI_API_BASE}/{model_name}:generateContent?key={api_key}"
            try:
                response = client.post(url, json=payload)
            except httpx.TimeoutException:
                last_error = f"Request timed out after {int(REQUEST_TIMEOUT_SECONDS)}s"
                continue
            except httpx.RequestError as exc:
                last_error = f"Network error: {exc}"
                continue

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    answer_parts = [p.get("text", "") for p in parts if p.get("text")]
                    answer = "\n".join(answer_parts).strip()
                    if answer:
                        return answer, model_name, was_truncated
                last_error = "Gemini returned an empty response."
                continue

            # Fail immediately on authentication errors
            if response.status_code in (401, 403):
                raise RuntimeError(
                    "Gemini API authentication failed. Check that GEMINI_API_KEY is valid."
                )

            try:
                err_msg = response.json().get("error", {}).get("message", response.text[:200])
            except Exception:
                err_msg = response.text[:200]
            last_error = f"HTTP {response.status_code} ({model_name}): {err_msg}"
    finally:
        if owns_client:
            client.close()

    raise RuntimeError(f"Could not get an answer from Gemini API: {last_error}")


def prompt_for_pdf_path() -> Path:
    """Interactively prompt the user until a valid PDF path is given."""
    while True:
        raw = input("Enter the path to your PDF document: ")
        if raw.strip().lower() in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        path = clean_user_path(raw)
        if not str(path):
            print("Please enter a valid file path.")
            continue
        return path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Answer questions from a PDF document using the Gemini API."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="Path to the PDF document.",
    )
    parser.add_argument(
        "-q",
        "--question",
        help="Ask a single question and exit (omit for interactive Q&A mode).",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=os.getenv("GEMINI_MODEL", "").strip() or None,
        help="Optional Gemini model name (default: gemini-flash-lite-latest).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = load_api_key()
    if not api_key:
        print(
            "Error: GEMINI_API_KEY is missing.\n"
            "Copy .env.example to .env and set GEMINI_API_KEY=your_key_here.",
            file=sys.stderr,
        )
        return 1

    try:
        pdf_path = clean_user_path(args.pdf) if args.pdf else prompt_for_pdf_path()
        doc = extract_pdf(pdf_path)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if doc.has_text:
        print(
            f"Loaded '{doc.path.name}' ({doc.page_count} page(s), "
            f"{doc.total_chars:,} extracted characters)."
        )
    else:
        print(
            f"Loaded '{doc.path.name}' ({doc.page_count} page(s), no embedded text; "
            "using direct PDF upload to Gemini)."
        )

    models = [args.model] if args.model else None

    if args.question:
        try:
            answer, model_used, truncated = ask_gemini(
                doc, args.question, api_key=api_key, models=models
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if truncated:
            print("[Note: Large PDF; answered using the most relevant pages.]")
        print(f"\nAnswer ({model_used}):\n{answer}")
        return 0

    print("Interactive Q&A started. Type 'exit' or 'quit' to finish.\n")
    history: list[tuple[str, str]] = []

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break

        try:
            print("Thinking...", flush=True)
            answer, model_used, truncated = ask_gemini(
                doc,
                question,
                api_key=api_key,
                models=models,
                history=history[-4:],
            )
            history.append((question, answer))
            if truncated:
                print("[Note: Large PDF; answered using the most relevant pages.]")
            print(f"\nAnswer ({model_used}):\n{answer}\n")
        except Exception as exc:
            print(f"Error: {exc}\n", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
