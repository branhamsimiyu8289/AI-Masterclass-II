import base64
import tempfile
import unittest
from pathlib import Path

import httpx

import pdf_qa


def make_test_pdf(path: Path, page_texts: list[str]) -> Path:
    """Create a minimal valid multi-page PDF with extractable text."""
    objects: list[bytes] = []

    # 1: Catalog, 2: Pages, 3: Font (Helvetica)
    page_obj_nums = []
    next_obj = 4
    for _ in page_texts:
        page_obj_nums.append(next_obj)
        next_obj += 2  # Page object + Content stream object

    kids_str = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(
        f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_texts)} >>\nendobj\n".encode("ascii")
    )
    objects.append(
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    for idx, text in enumerate(page_texts):
        page_num = page_obj_nums[idx]
        content_num = page_num + 1
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")

        objects.append(
            f"{page_num} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>\n"
            f"endobj\n".encode("ascii")
        )
        objects.append(
            f"{content_num} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream\nendobj\n"
        )

    header = b"%PDF-1.4\n"
    body = bytearray(header)
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
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(body))
    return path


class PdfQaTests(unittest.TestCase):
    def test_clean_user_path_strips_quotes_and_spaces(self) -> None:
        cleaned = pdf_qa.clean_user_path('  "C:\\docs\\sample.pdf"  ')
        self.assertEqual(cleaned, Path("C:\\docs\\sample.pdf"))

    def test_extract_pdf_reads_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = make_test_pdf(
                Path(tmp) / "contract.pdf",
                [
                    "Supplier Agreement between Acme Ltd and Nairobi Traders.",
                    "Payment terms are Net 30 days via M-Pesa Paybill 123456.",
                ],
            )
            doc = pdf_qa.extract_pdf(pdf_path)
            self.assertEqual(doc.page_count, 2)
            self.assertTrue(doc.has_text)
            self.assertIn("Acme Ltd", doc.pages[0][1])
            self.assertIn("Net 30 days", doc.pages[1][1])

    def test_extract_pdf_missing_or_wrong_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.pdf"
            with self.assertRaises(FileNotFoundError):
                pdf_qa.extract_pdf(missing)

            txt_file = Path(tmp) / "notes.txt"
            txt_file.write_text("hello", encoding="utf-8")
            with self.assertRaises(ValueError):
                pdf_qa.extract_pdf(txt_file)

    def test_select_relevant_pages_for_large_document(self) -> None:
        doc = pdf_qa.PdfDocument(
            path=Path("big.pdf"),
            pages=[
                (1, "Document overview and introduction."),
                (2, "General background information about operations."),
                (3, "Penalty clause: late delivery incurs 5 percent fee per week."),
            ],
            file_size_bytes=1000,
        )
        context, truncated = pdf_qa.select_relevant_pages(
            doc, "What is the late delivery penalty fee?", max_chars=140
        )
        self.assertTrue(truncated)
        self.assertIn("[Page 3]", context)
        self.assertIn("5 percent", context)

    def test_build_contents_inline_fallback_for_scanned_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "scanned.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n%fake-scanned-bytes")
            doc = pdf_qa.PdfDocument(
                path=pdf_path,
                pages=[(1, "")],
                file_size_bytes=pdf_path.stat().st_size,
            )
            contents, truncated = pdf_qa.build_contents(doc, "Summarize this page")
            self.assertFalse(truncated)
            part = contents[0]["parts"][0]
            self.assertEqual(part["inline_data"]["mime_type"], "application/pdf")
            decoded = base64.b64decode(part["inline_data"]["data"])
            self.assertTrue(decoded.startswith(b"%PDF-1.4"))

    def test_ask_gemini_success_and_model_fallback(self) -> None:
        doc = pdf_qa.PdfDocument(
            path=Path("policy.pdf"),
            pages=[(1, "Refunds are issued within 7 business days.")],
            file_size_bytes=200,
        )
        seen_urls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_urls.append(str(request.url))
            if "model-a" in str(request.url):
                return httpx.Response(503, json={"error": {"message": "Busy"}})
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "Refunds take 7 business days [Page 1]."}
                                ]
                            }
                        }
                    ]
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            answer, model_used, truncated = pdf_qa.ask_gemini(
                doc,
                "How long do refunds take?",
                api_key="test-key",
                models=["model-a", "model-b"],
                http_client=client,
            )

        self.assertEqual(model_used, "model-b")
        self.assertFalse(truncated)
        self.assertIn("7 business days", answer)
        self.assertEqual(len(seen_urls), 2)

    def test_ask_gemini_auth_error_fails_immediately(self) -> None:
        doc = pdf_qa.PdfDocument(
            path=Path("policy.pdf"),
            pages=[(1, "Sample text.")],
            file_size_bytes=100,
        )
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(401, json={"error": {"message": "Invalid key"}})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(RuntimeError):
                pdf_qa.ask_gemini(
                    doc,
                    "What does it say?",
                    api_key="bad-key",
                    models=["model-a", "model-b"],
                    http_client=client,
                )

        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
