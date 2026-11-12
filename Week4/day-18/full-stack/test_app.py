"""
Integration test suite for the Day 18 Full-Stack Egg Production Tracker.
Tests:
1. Web interface (HTML page with form, table, and fetch script).
2. Four POST requests across two sheds (Shed 1 and Shed 2).
3. Verification of GET /api/eggs returning updated running totals and summary.
4. Input validation (missing fields, negative counts, invalid dates).
"""

import unittest
import os
import sqlite3
import tempfile
from contextlib import closing

from app import app, database


class FullStackEggTrackerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        app.config["DATABASE_PATH"] = os.path.join(cls.temp_dir.name, "test-eggs.db")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["RESET_TOKEN"] = "test-reset-token"
        self.client = app.test_client()
        with database() as db:
            db.execute("DELETE FROM egg_records")

    def test_browser_page_renders_form_and_table(self):
        """Verify GET / returns the HTML page containing the form, table, and fetch logic."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Check essential UI elements
        self.assertIn("Kiambu Farm - Egg Production Tracker", html)
        self.assertIn("id=\"eggForm\"", html)
        self.assertIn("id=\"shedName\"", html)
        self.assertIn("id=\"logDate\"", html)
        self.assertIn("id=\"eggCount\"", html)
        self.assertIn("id=\"recordsTable\"", html)
        self.assertIn("fetch('/api/eggs'", html)

    def test_log_records_across_two_sheds_and_verify_running_total(self):
        """
        Log records for at least two sheds and confirm that running totals
        and table data update correctly.
        """
        # 1. Post Record 1 - Shed 1
        r1 = self.client.post("/api/eggs", json={
            "shed_name": "Shed 1",
            "date": "2026-11-10",
            "count": 140
        })
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.get_json()["record"]["count"], 140)

        # 2. Post Record 2 - Shed 2
        r2 = self.client.post("/api/eggs", json={
            "shed_name": "Shed 2",
            "date": "2026-11-10",
            "count": 165
        })
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r2.get_json()["record"]["count"], 165)

        # 3. Post Record 3 - Shed 1
        r3 = self.client.post("/api/eggs", json={
            "shed_name": "Shed 1",
            "date": "2026-11-11",
            "count": 145
        })
        self.assertEqual(r3.status_code, 201)

        # 4. Post Record 4 - Shed 2
        r4 = self.client.post("/api/eggs", json={
            "shed_name": "Shed 2",
            "date": "2026-11-11",
            "count": 170
        })
        self.assertEqual(r4.status_code, 201)

        # 5. Call GET /api/eggs as JavaScript fetch() does
        res = self.client.get("/api/eggs")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Check totals
        self.assertEqual(data["total_records"], 4)
        self.assertEqual(data["total_eggs"], 620)
        self.assertEqual(data["shed_breakdown"]["Shed 1"], 285)
        self.assertEqual(data["shed_breakdown"]["Shed 2"], 335)

        # Check running totals calculation
        records = data["records"]
        self.assertEqual(records[0]["running_total"], 140)
        self.assertEqual(records[1]["running_total"], 305)  # 140 + 165
        self.assertEqual(records[2]["running_total"], 450)  # 305 + 145
        self.assertEqual(records[3]["running_total"], 620)  # 450 + 170

    def test_validation_errors(self):
        """Test API bad request responses for invalid data."""
        # Empty shed name
        r1 = self.client.post("/api/eggs", json={"shed_name": "", "date": "2026-11-11", "count": 100})
        self.assertEqual(r1.status_code, 400)

        # Negative count
        r2 = self.client.post("/api/eggs", json={"shed_name": "Shed 1", "date": "2026-11-11", "count": -10})
        self.assertEqual(r2.status_code, 400)

        # Invalid date format
        r3 = self.client.post("/api/eggs", json={"shed_name": "Shed 1", "date": "not-a-date", "count": 100})
        self.assertEqual(r3.status_code, 400)

    def test_records_are_written_to_persistent_sqlite_database(self):
        response = self.client.post("/api/eggs", json={
            "shed_name": "Shed 1",
            "date": "2026-11-11",
            "count": 120
        })
        self.assertEqual(response.status_code, 201)

        with closing(sqlite3.connect(app.config["DATABASE_PATH"])) as db:
            row = db.execute("SELECT shed_name, count FROM egg_records").fetchone()
        self.assertEqual(row, ("Shed 1", 120))

    def test_health_check_includes_database(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_reset_endpoint_is_disabled_without_token_and_protected_with_token(self):
        app.config["RESET_TOKEN"] = None
        self.assertEqual(self.client.delete("/api/eggs").status_code, 404)

        app.config["RESET_TOKEN"] = "test-reset-token"
        self.assertEqual(self.client.delete("/api/eggs").status_code, 403)
        response = self.client.delete(
            "/api/eggs",
            headers={"Authorization": "Bearer test-reset-token"},
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
