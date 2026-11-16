import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class FileAutomationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_organize_previews_then_moves_files_into_categories(self):
        (self.root / "photo.JPG").write_text("image")
        (self.root / "notes.txt").write_text("document")
        (self.root / "run.py").write_text("script")
        (self.root / "unknown.bin").write_text("other")

        preview = app.organize_files(self.root)

        self.assertEqual(len(preview), 4)
        self.assertTrue(all(message.startswith("Would move:") for message in preview))
        self.assertFalse((self.root / "Images").exists())

        app.organize_files(self.root, dry_run=False)

        self.assertEqual((self.root / "Images" / "photo.JPG").read_text(), "image")
        self.assertEqual((self.root / "Documents" / "notes.txt").read_text(), "document")
        self.assertEqual((self.root / "Scripts" / "run.py").read_text(), "script")
        self.assertEqual((self.root / "Other" / "unknown.bin").read_text(), "other")
        self.assertEqual(app.organize_files(self.root), ["No files to organize."])

    def test_copy_previews_and_refuses_to_overwrite(self):
        source = self.root / "source.txt"
        destination = self.root / "destination.txt"
        source.write_text("original")

        message = app.copy_file(source, destination)

        self.assertIn("Would copy:", message)
        self.assertFalse(destination.exists())
        app.copy_file(source, destination, dry_run=False)
        self.assertEqual(destination.read_text(), "original")
        with self.assertRaises(FileExistsError):
            app.copy_file(source, destination, dry_run=False)

    def test_backup_copies_only_spreadsheets_to_month_folder(self):
        source = self.root / "reports"
        archive = self.root / "archive"
        source.mkdir()
        (source / "sales.xlsx").write_text("report")
        (source / "notes.txt").write_text("not a report")

        with patch("app.datetime") as mocked_datetime:
            mocked_datetime.now.return_value.strftime.return_value = "2026-11"
            preview = app.backup_reports(source, archive)
            self.assertEqual(len(preview), 1)
            self.assertFalse(archive.exists())

            app.backup_reports(source, archive, dry_run=False)

        self.assertEqual(
            (archive / "2026-11" / "sales.xlsx").read_text(), "report"
        )
        self.assertTrue((source / "sales.xlsx").exists())
        self.assertFalse((archive / "2026-11" / "notes.txt").exists())

    def test_rename_previews_then_renames_files_in_sorted_order(self):
        (self.root / "b.png").write_text("second")
        (self.root / "a.jpg").write_text("first")

        preview = app.rename_photos(self.root, "ORD-42")

        self.assertEqual(len(preview), 2)
        self.assertTrue((self.root / "a.jpg").exists())
        self.assertFalse((self.root / "ORD-42_photo_01.jpg").exists())

        app.rename_photos(self.root, "ORD-42", dry_run=False)

        self.assertEqual(
            (self.root / "ORD-42_photo_01.jpg").read_text(), "first"
        )
        self.assertEqual(
            (self.root / "ORD-42_photo_02.png").read_text(), "second"
        )
        self.assertEqual(
            app.rename_photos(self.root, "ORD-42"), ["Files are already named."]
        )

    def test_rename_rejects_order_number_that_escapes_folder(self):
        (self.root / "photo.jpg").write_text("image")

        with self.assertRaises(ValueError):
            app.rename_photos(self.root, "..\\outside")

        self.assertEqual([path.name for path in self.root.iterdir()], ["photo.jpg"])

    def test_cli_mutations_require_apply_flag(self):
        source = self.root / "source.txt"
        destination = self.root / "destination.txt"
        source.write_text("content")
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            self.assertEqual(
                app.main(["copy", str(source), str(destination)]), 0
            )

        self.assertIn("Would copy:", output.getvalue())
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
