"""Unit tests for the hardened Document Handler in Week6/day-29."""

from __future__ import annotations

import csv
import io
import logging
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx
from docx import Document

import document_handler as dh


def make_test_pdf(path: Path, page_texts: list[str]) -> Path:
    """Create a minimal valid multi-page PDF with extractable text."""
    objects: list[bytes] = []
    page_obj_nums: list[int] = []
    next_obj = 4
    for _ in page_texts:
        page_obj_nums.append(next_obj)
        next_obj += 2

    kids_str = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(
        f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_texts)} >>\nendobj\n".encode(
            "ascii"
        )
    )
    objects.append(
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    for idx, text in enumerate(page_texts):
        page_num = page_obj_nums[idx]
        content_num = page_num + 1
        if text:
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
        else:
            stream = b""

        objects.append(
            f"{page_num} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>\n"
            f"endobj\n".encode("ascii")
        )
        objects.append(
            f"{content_num} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode(
                "ascii"
            )
            + stream
            + b"\nendstream\nendobj\n"
        )

    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body.extend(obj)

    xref_pos = len(body)
    body.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    body.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    path.write_bytes(bytes(body))
    return path


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_data: object = None,
        headers: dict[str, str] | None = None,
        invalid_json: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {}
        self._invalid_json = invalid_json

    def json(self) -> object:
        if self._invalid_json:
            raise ValueError("Invalid JSON")
        return self._json_data


class _FakeClient:
    def __init__(self, actions: list[object]) -> None:
        self.actions = list(actions)
        self.calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> _FakeResponse:
        self.calls.append((url, headers or {}, json or {}))
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        assert isinstance(action, _FakeResponse)
        return action

    def close(self) -> None:
        pass


class PdfExtractionTests(unittest.TestCase):
    def test_multipage_text_does_not_concatenate_words_across_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = make_test_pdf(
                Path(tmpdir) / "contract.pdf",
                ["End of page one", "Start of page two"],
            )
            result = dh.extract_pdf_text(pdf)
            self.assertEqual(result.page_count, 2)
            self.assertEqual(result.text, "End of page one\n\nStart of page two")
            self.assertNotIn("oneStart", result.text)

    def test_corrupt_pdf_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_pdf = Path(tmpdir) / "corrupt.pdf"
            bad_pdf.write_bytes(b"not a valid pdf file")
            with self.assertRaises(ValueError):
                dh.extract_pdf_text(bad_pdf)

    def test_missing_pdf_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                dh.extract_pdf_text(Path(tmpdir) / "missing.pdf")


class GeminiRetryAndExtractionTests(unittest.TestCase):
    def test_retries_transient_429_and_503_with_exponential_backoff(self) -> None:
        sleeps: list[float] = []
        client = _FakeClient(
            [
                _FakeResponse(429),
                _FakeResponse(503),
                _FakeResponse(
                    200,
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {"text": "thinking...", "thought": True},
                                        {"text": "Parties: Acme & Kamau"},
                                    ]
                                }
                            }
                        ]
                    },
                ),
            ]
        )

        with self.assertLogs("document_handler", level="INFO") as logs:
            answer, model_used = dh.call_gemini_with_retry(
                prompt="Extract contract details",
                api_key="test-key-secret",
                models=("model-a", "model-b"),
                max_retries=3,
                base_delay=1.5,
                sleep_fn=sleeps.append,
                client=client,  # type: ignore[arg-type]
            )

        self.assertEqual(answer, "Parties: Acme & Kamau")
        self.assertEqual(model_used, "model-a")
        self.assertEqual(sleeps, [1.5, 3.0])
        self.assertEqual(len(client.calls), 3)
        joined_logs = "\n".join(logs.output)
        self.assertIn("Retryable HTTP 429", joined_logs)
        self.assertIn("Retryable HTTP 503", joined_logs)
        self.assertNotIn("test-key-secret", joined_logs)

    def test_respects_retry_after_header(self) -> None:
        sleeps: list[float] = []
        client = _FakeClient(
            [
                _FakeResponse(429, headers={"Retry-After": "4"}),
                _FakeResponse(
                    200,
                    {"candidates": [{"content": {"parts": [{"text": "Done"}]}}]},
                ),
            ]
        )
        answer, _ = dh.call_gemini_with_retry(
            prompt="Hi",
            api_key="secret",
            models=("model-a",),
            max_retries=2,
            base_delay=1.0,
            sleep_fn=sleeps.append,
            client=client,  # type: ignore[arg-type]
        )
        self.assertEqual(answer, "Done")
        self.assertEqual(sleeps, [4.0])

    def test_timeout_retries_then_falls_back_to_second_model(self) -> None:
        sleeps: list[float] = []
        client = _FakeClient(
            [
                httpx.TimeoutException("timeout 1"),
                httpx.RequestError("conn reset"),
                _FakeResponse(
                    200,
                    {"candidates": [{"content": {"parts": [{"text": "Fallback OK"}]}}]},
                ),
            ]
        )

        with self.assertLogs("document_handler", level="WARNING") as logs:
            answer, model_used = dh.call_gemini_with_retry(
                prompt="Extract",
                api_key="secret",
                models=("model-a", "model-b"),
                max_retries=2,
                base_delay=0.5,
                sleep_fn=sleeps.append,
                client=client,  # type: ignore[arg-type]
            )

        self.assertEqual(answer, "Fallback OK")
        self.assertEqual(model_used, "model-b")
        self.assertEqual(sleeps, [0.5])
        self.assertIn("Timeout calling 'model-a'", "\n".join(logs.output))

    def test_auth_error_does_not_retry_or_fallback(self) -> None:
        sleeps: list[float] = []
        client = _FakeClient([_FakeResponse(401)])

        with self.assertLogs("document_handler", level="ERROR"):
            with self.assertRaises(dh.GeminiAuthError):
                dh.call_gemini_with_retry(
                    prompt="Extract",
                    api_key="bad-key",
                    models=("model-a", "model-b"),
                    max_retries=3,
                    sleep_fn=sleeps.append,
                    client=client,  # type: ignore[arg-type]
                )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(sleeps, [])

    def test_bad_request_400_falls_back_without_sleeping_and_raises_if_all_fail(self) -> None:
        sleeps: list[float] = []
        client = _FakeClient([_FakeResponse(400), _FakeResponse(400)])

        with self.assertLogs("document_handler", level="ERROR"):
            with self.assertRaises(RuntimeError) as ctx:
                dh.call_gemini_with_retry(
                    prompt="Extract",
                    api_key="secret",
                    models=("model-a", "model-b"),
                    max_retries=3,
                    sleep_fn=sleeps.append,
                    client=client,  # type: ignore[arg-type]
                )

        self.assertIn("All Gemini models failed", str(ctx.exception))
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(sleeps, [])

    def test_missing_api_key_raises_runtime_error(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            dh.call_gemini_with_retry(prompt="Extract", api_key="")
        self.assertIn("GEMINI_API_KEY is missing", str(ctx.exception))

    def test_malformed_or_empty_candidates_handled_safely(self) -> None:
        sleeps: list[float] = []
        client = _FakeClient(
            [
                _FakeResponse(200, json_data={"candidates": []}),
                _FakeResponse(200, invalid_json=True),
                _FakeResponse(
                    200,
                    json_data={"candidates": [{"content": {"parts": [{"text": "Valid"}]}}]},
                ),
            ]
        )
        answer, model_used = dh.call_gemini_with_retry(
            prompt="Extract",
            api_key="secret",
            models=("model-a", "model-b"),
            max_retries=2,
            base_delay=0.1,
            sleep_fn=sleeps.append,
            client=client,  # type: ignore[arg-type]
        )
        self.assertEqual(answer, "Valid")
        self.assertEqual(model_used, "model-b")

    def test_empty_scanned_contract_raises_before_calling_gemini(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            blank_pdf = make_test_pdf(Path(tmpdir) / "scanned.pdf", [""])
            client = _FakeClient([])
            with self.assertRaises(ValueError) as ctx:
                dh.extract_contract_details(
                    blank_pdf,
                    api_key="secret",
                    client=client,  # type: ignore[arg-type]
                )
            self.assertIn("no extractable text", str(ctx.exception))
            self.assertEqual(client.calls, [])

    def test_extract_contract_details_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            contract = make_test_pdf(
                Path(tmpdir) / "supplier_contract.pdf",
                ["Party A: Kamau Stores", "Payment: Net 30 days"],
            )
            client = _FakeClient(
                [
                    _FakeResponse(
                        200,
                        {"candidates": [{"content": {"parts": [{"text": "Net 30 days"}]}}]},
                    )
                ]
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = dh.extract_contract_details(
                    contract,
                    api_key="secret",
                    client=client,  # type: ignore[arg-type]
                )
            self.assertEqual(result, "Net 30 days")
            self.assertIn("Net 30 days", buf.getvalue())
            sent_prompt = client.calls[0][2]["contents"][0]["parts"][0]["text"]
            self.assertIn("Party A: Kamau Stores\n\nPayment: Net 30 days", sent_prompt)


class SalesReportAndIndexingTests(unittest.TestCase):
    def test_sales_report_calculates_dynamic_total_and_period(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "nested" / "report.docx"
            rows = [("Beans", 10, 1500), ("Sugar", 5, 2500)]
            saved = dh.create_monthly_sales_report(
                output_path=out_path,
                rows=rows,
                report_date=date(2026, 3, 15),
            )
            self.assertTrue(saved.is_file())
            doc = Document(str(saved))
            full_text = "\n".join(p.text for p in doc.paragraphs)
            self.assertIn("March 2026: KES 4,000.", full_text)
            self.assertIn("2026-03-15", full_text)
            self.assertEqual(len(doc.tables[0].rows), 3)

    def test_index_invoices_case_insensitive_sorted_and_survives_corrupt_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            inv_dir = Path(tmpdir) / "invoices"
            inv_dir.mkdir()
            make_test_pdf(inv_dir / "b_invoice.PDF", ["Line 1\nLine 2"])
            make_test_pdf(inv_dir / "a_invoice.pdf", ["Alpha invoice"])
            (inv_dir / "c_broken.pdf").write_bytes(b"corrupt")
            (inv_dir / "subdir.pdf").mkdir()
            (inv_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

            csv_out = Path(tmpdir) / "out" / "invoice_index.csv"
            with self.assertLogs("document_handler", level="WARNING") as logs:
                rows = dh.index_invoices(inv_dir, csv_out)

            self.assertEqual([r["file"] for r in rows], ["a_invoice.pdf", "b_invoice.PDF", "c_broken.pdf"])
            self.assertEqual(rows[0]["status"], "ok")
            self.assertEqual(rows[1]["status"], "ok")
            self.assertEqual(rows[2]["status"], "error")
            self.assertIn("Skipping unreadable invoice 'c_broken.pdf'", "\n".join(logs.output))

            with csv_out.open(encoding="utf-8") as f:
                csv_rows = list(csv.DictReader(f))
            self.assertEqual(len(csv_rows), 3)
            self.assertEqual(csv_rows[1]["preview"], "Line 1 Line 2")


class CliAndLoggingTests(unittest.TestCase):
    def test_configure_logging_writes_to_file_and_avoids_duplicate_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "logs" / "app.log"
            dh.configure_logging(level="DEBUG", log_file=log_path)
            dh.configure_logging(level="INFO", log_file=log_path)
            self.assertEqual(len(dh.logger.handlers), 2)
            dh.logger.info("hello log")
            for handler in list(dh.logger.handlers):
                dh.logger.removeHandler(handler)
                handler.close()
            self.assertIn("hello log", log_path.read_text(encoding="utf-8"))

    def test_main_runs_cleanly_when_optional_inputs_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            code = dh.main(
                [
                    "--invoice",
                    str(tmp / "missing_invoice.pdf"),
                    "--contract",
                    str(tmp / "missing_contract.pdf"),
                    "--report",
                    str(tmp / "report.docx"),
                    "--invoices-dir",
                    str(tmp / "missing_dir"),
                    "--index-csv",
                    str(tmp / "index.csv"),
                    "--log-file",
                    str(tmp / "run.log"),
                ]
            )
            for handler in list(dh.logger.handlers):
                dh.logger.removeHandler(handler)
                handler.close()
            self.assertEqual(code, 0)
            self.assertTrue((tmp / "report.docx").is_file())
            self.assertTrue((tmp / "run.log").is_file())

    def test_main_returns_nonzero_on_corrupt_invoice(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad_invoice = tmp / "bad.pdf"
            bad_invoice.write_bytes(b"corrupt")
            with patch("sys.stderr", new_callable=io.StringIO):
                code = dh.main(
                    [
                        "--invoice",
                        str(bad_invoice),
                        "--contract",
                        str(tmp / "missing_contract.pdf"),
                        "--report",
                        str(tmp / "report.docx"),
                        "--invoices-dir",
                        str(tmp / "missing_dir"),
                        "--log-file",
                        str(tmp / "run.log"),
                    ]
                )
            for handler in list(dh.logger.handlers):
                dh.logger.removeHandler(handler)
                handler.close()
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
