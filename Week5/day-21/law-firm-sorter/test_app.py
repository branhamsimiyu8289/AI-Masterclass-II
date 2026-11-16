import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import app


class LawFirmDocumentSorterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_category_mappings(self):
        self.assertEqual(app.get_category_for_file("contract.docx"), "Contracts")
        self.assertEqual(app.get_category_for_file("agreement.doc"), "Contracts")
        self.assertEqual(app.get_category_for_file("DEED.DOCX"), "Contracts")

        self.assertEqual(app.get_category_for_file("photo.jpg"), "Evidence")
        self.assertEqual(app.get_category_for_file("scene.jpeg"), "Evidence")
        self.assertEqual(app.get_category_for_file("id.png"), "Evidence")
        self.assertEqual(app.get_category_for_file("EVIDENCE.PNG"), "Evidence")

        self.assertEqual(app.get_category_for_file("motion.pdf"), "Filings")
        self.assertEqual(app.get_category_for_file("BRIEF.PDF"), "Filings")

        self.assertEqual(app.get_category_for_file("notes.txt"), "Correspondence")
        self.assertEqual(app.get_category_for_file("thread.eml"), "Correspondence")
        self.assertEqual(app.get_category_for_file("CLIENT.EML"), "Correspondence")

        self.assertEqual(app.get_category_for_file("disbursements.xlsx"), "Other")
        self.assertEqual(app.get_category_for_file("recording.mp3"), "Other")
        self.assertEqual(app.get_category_for_file("unknown_blob"), "Other")

    def test_sort_documents_previews_then_moves_files_and_logs(self):
        (self.root / "Contract_FINAL_v3.docx").write_text("contract text", encoding="utf-8")
        (self.root / "Lease.doc").write_text("lease text", encoding="utf-8")
        (self.root / "IMG_4827.jpg").write_text("image bytes", encoding="utf-8")
        (self.root / "scene.jpeg").write_text("scene bytes", encoding="utf-8")
        (self.root / "id.png").write_text("id card", encoding="utf-8")
        (self.root / "scan001.pdf").write_text("court filing pdf", encoding="utf-8")
        (self.root / "notes.txt").write_text("interview notes", encoding="utf-8")
        (self.root / "email.eml").write_text("email headers and body", encoding="utf-8")
        (self.root / "fee.xlsx").write_text("excel sheet", encoding="utf-8")
        (self.root / "audio.mp3").write_text("audio data", encoding="utf-8")

        # 1. Preview mode (dry_run=True)
        preview = app.sort_documents(self.root, dry_run=True)

        self.assertEqual(len(preview), 10)
        self.assertTrue(all(msg.startswith("Would move:") for msg in preview))
        self.assertFalse((self.root / "Contracts").exists())
        self.assertFalse((self.root / "Evidence").exists())
        self.assertFalse((self.root / "Filings").exists())
        self.assertFalse((self.root / "Correspondence").exists())
        self.assertFalse((self.root / "Other").exists())
        self.assertFalse((self.root / "sort_log.txt").exists())

        # 2. Execution mode (dry_run=False)
        result = app.sort_documents(self.root, dry_run=False)

        self.assertEqual(len(result), 10)
        self.assertTrue(all(msg.startswith("move:") for msg in result))

        # Check subfolder sorting
        self.assertEqual(
            (self.root / "Contracts" / "Contract_FINAL_v3.docx").read_text(encoding="utf-8"),
            "contract text",
        )
        self.assertEqual(
            (self.root / "Contracts" / "Lease.doc").read_text(encoding="utf-8"),
            "lease text",
        )
        self.assertEqual(
            (self.root / "Evidence" / "IMG_4827.jpg").read_text(encoding="utf-8"),
            "image bytes",
        )
        self.assertEqual(
            (self.root / "Evidence" / "scene.jpeg").read_text(encoding="utf-8"),
            "scene bytes",
        )
        self.assertEqual(
            (self.root / "Evidence" / "id.png").read_text(encoding="utf-8"),
            "id card",
        )
        self.assertEqual(
            (self.root / "Filings" / "scan001.pdf").read_text(encoding="utf-8"),
            "court filing pdf",
        )
        self.assertEqual(
            (self.root / "Correspondence" / "notes.txt").read_text(encoding="utf-8"),
            "interview notes",
        )
        self.assertEqual(
            (self.root / "Correspondence" / "email.eml").read_text(encoding="utf-8"),
            "email headers and body",
        )
        self.assertEqual(
            (self.root / "Other" / "fee.xlsx").read_text(encoding="utf-8"),
            "excel sheet",
        )
        self.assertEqual(
            (self.root / "Other" / "audio.mp3").read_text(encoding="utf-8"),
            "audio data",
        )

        # Check sort_log.txt was created and has 10 entries with timestamps
        log_path = self.root / "sort_log.txt"
        self.assertTrue(log_path.exists())
        log_content = log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(log_content), 10)
        for line in log_content:
            self.assertTrue(line.startswith("["))
            self.assertIn("] ", line)
            self.assertIn(" -> ", line)

        # Running again reports no files to organize
        self.assertEqual(app.sort_documents(self.root, dry_run=False), ["No files to organize."])

    def test_sort_documents_ignores_log_file_and_subdirectories(self):
        log_file = self.root / "sort_log.txt"
        log_file.write_text("[2026-11-16 10:00:00] Initial log line\n", encoding="utf-8")

        subfolder = self.root / "Subdir"
        subfolder.mkdir()
        (subfolder / "nested.pdf").write_text("nested", encoding="utf-8")

        file_to_sort = self.root / "doc.pdf"
        file_to_sort.write_text("pdf content", encoding="utf-8")

        app.sort_documents(self.root, dry_run=False)

        # Log file remains in root and is not moved into Correspondence
        self.assertTrue(log_file.exists())
        # Nested directory is untouched
        self.assertTrue((subfolder / "nested.pdf").exists())
        # doc.pdf is moved to Filings
        self.assertTrue((self.root / "Filings" / "doc.pdf").exists())

    def test_sort_documents_custom_log_file(self):
        custom_log = self.root / "logs" / "custom_audit.txt"
        (self.root / "contract.docx").write_text("content", encoding="utf-8")

        app.sort_documents(self.root, dry_run=False, log_file=custom_log)

        self.assertTrue(custom_log.exists())
        self.assertIn("contract.docx", custom_log.read_text(encoding="utf-8"))

    def test_sort_refuses_to_overwrite_existing_destination(self):
        contracts_dir = self.root / "Contracts"
        contracts_dir.mkdir()
        (contracts_dir / "agreement.docx").write_text("already here", encoding="utf-8")
        (self.root / "agreement.docx").write_text("new version", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            app.sort_documents(self.root, dry_run=False)

    def test_create_dummy_files(self):
        files = app.create_dummy_files(self.root)
        self.assertGreaterEqual(len(files), 10)
        self.assertTrue(all(f.exists() for f in files))
        self.assertTrue((self.root / "Contract_FINAL_v3.docx").exists())
        self.assertTrue((self.root / "scan001.pdf").exists())
        self.assertTrue((self.root / "IMG_4827.jpg").exists())

    def test_cli_sort_preview_and_apply(self):
        app.create_dummy_files(self.root)

        preview_output = io.StringIO()
        with contextlib.redirect_stdout(preview_output):
            exit_code = app.main(["sort", str(self.root)])
        self.assertEqual(exit_code, 0)
        self.assertIn("Would move:", preview_output.getvalue())
        self.assertFalse((self.root / "Contracts").exists())

        apply_output = io.StringIO()
        with contextlib.redirect_stdout(apply_output):
            exit_code = app.main(["sort", str(self.root), "--apply"])
        self.assertEqual(exit_code, 0)
        self.assertIn("Organized documents in", apply_output.getvalue())
        self.assertIn("Audit log written to:", apply_output.getvalue())
        self.assertTrue((self.root / "Contracts").exists())
        self.assertTrue((self.root / "sort_log.txt").exists())

    def test_cli_dummy_generation(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = app.main(["create-dummy", str(self.root)])
        self.assertEqual(exit_code, 0)
        self.assertIn("Created", output.getvalue())
        self.assertTrue((self.root / "Contract_FINAL_v3.docx").exists())

    def test_cli_without_command_prints_help(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(app.main([]), 0)
        self.assertIn("usage: ", output.getvalue())
        self.assertIn("sort", output.getvalue())


if __name__ == "__main__":
    unittest.main()
