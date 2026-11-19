"""
Unit and Integration Tests for Daily Retail Sales Reporter & Single-Line Audit Logger
"""

import csv
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from sales_reporter import (
    build_email_contents,
    format_currency_kes,
    log_run_summary,
    parse_sales_csv,
    run_sales_report_pipeline,
)


class TestSalesReporterAndLogger(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.csv_path = self.temp_path / "test_sales.csv"
        self.log_path = self.temp_path / "run_log.txt"

        # Create a sample test CSV with 10 rows
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "transaction_id", "timestamp", "item_name", "category",
                "quantity_sold", "unit_price", "payment_method",
                "stock_remaining", "restock_threshold"
            ])
            writer.writerow(["TXN-01", "2026-11-19 08:30:00", "Brookside Milk 500ml", "Dairy", 5, 65.0, "M-Pesa", 15, 10])
            writer.writerow(["TXN-02", "2026-11-19 09:00:00", "Pembe Flour 2kg", "Staples", 2, 215.0, "Cash", 3, 10])  # Low stock!
            writer.writerow(["TXN-03", "2026-11-19 09:45:00", "Kabras Sugar 1kg", "Staples", 3, 160.0, "M-Pesa", 8, 12])  # Low stock!
            writer.writerow(["TXN-04", "2026-11-19 10:15:00", "Broadways Bread 400g", "Bakery", 4, 65.0, "Cash", 20, 10])
            writer.writerow(["TXN-05", "2026-11-19 11:00:00", "Brookside Milk 500ml", "Dairy", 6, 65.0, "M-Pesa", 9, 10])  # Low stock!
            writer.writerow(["TXN-06", "2026-11-19 12:30:00", "Cooking Oil 1L", "Cooking Oils", 1, 320.0, "M-Pesa", 14, 5])
            writer.writerow(["TXN-07", "2026-11-19 13:15:00", "Indomie Noodles 120g", "Quick Meals", 10, 50.0, "Cash", 50, 20])
            writer.writerow(["TXN-08", "2026-11-19 14:00:00", "Royco Cubes 40s", "Seasoning", 2, 140.0, "Cash", 18, 10])
            writer.writerow(["TXN-09", "2026-11-19 15:20:00", "Ketepa Tea Leaves 250g", "Beverages", 1, 135.0, "M-Pesa", 12, 10])
            writer.writerow(["TXN-10", "2026-11-19 16:45:00", "Omo Washing Powder 500g", "Household", 2, 220.0, "M-Pesa", 4, 10])  # Low stock!

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # Core 4 Metrics Tests
    # -------------------------------------------------------------------------
    def test_total_revenue_calculation(self):
        """Metric 1: Total Revenue must equal sum of (quantity * unit_price)."""
        metrics = parse_sales_csv(self.csv_path)
        # 5*65 + 2*215 + 3*160 + 4*65 + 6*65 + 1*320 + 10*50 + 2*140 + 1*135 + 2*220 = 3560.0
        self.assertAlmostEqual(metrics["total_revenue"], 3560.0, places=2)

    def test_total_transactions_count(self):
        """Metric 2: Total Transactions must equal number of unique tickets."""
        metrics = parse_sales_csv(self.csv_path)
        self.assertEqual(metrics["total_transactions"], 10)
        self.assertEqual(metrics["rows_processed"], 10)

    def test_top_selling_item_identification(self):
        """Metric 3: Top-selling item by quantity should be Brookside Milk (11 units)."""
        metrics = parse_sales_csv(self.csv_path)
        top = metrics["top_selling_item"]
        self.assertEqual(top["item_name"], "Brookside Milk 500ml")
        self.assertEqual(top["quantity_sold"], 11)
        self.assertAlmostEqual(top["total_revenue"], 715.0, places=2)

    def test_restock_level_flag_trigger(self):
        """Metric 4: Flag must be True when items drop below threshold."""
        metrics = parse_sales_csv(self.csv_path)
        self.assertTrue(metrics["restock_flag"])
        low_names = [it["item_name"] for it in metrics["low_stock_items"]]
        self.assertIn("Pembe Flour 2kg", low_names)
        self.assertIn("Kabras Sugar 1kg", low_names)
        self.assertIn("Brookside Milk 500ml", low_names)
        self.assertIn("Omo Washing Powder 500g", low_names)

    def test_flexible_column_mapping(self):
        """Parser must accept column aliases (e.g. 'item', 'qty', 'price')."""
        alt_csv = self.temp_path / "alt_sales.csv"
        with open(alt_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["item", "qty", "price"])
            writer.writerow(["Milk 500ml", 3, 60.0])
            writer.writerow(["Bread 400g", 2, 70.0])

        metrics = parse_sales_csv(alt_csv)
        self.assertEqual(metrics["total_transactions"], 2)
        self.assertAlmostEqual(metrics["total_revenue"], 320.0, places=2)
        self.assertEqual(metrics["rows_processed"], 2)

    # -------------------------------------------------------------------------
    # Single-Line Audit Logger (run_log.txt) Tests
    # -------------------------------------------------------------------------
    def test_run_log_single_line_success_format(self):
        """
        Logger must write exactly ONE line with date, time, status, and rows processed.
        Pattern: YYYY-MM-DD HH:MM:SS | SUCCESS | <N> rows processed
        """
        fixed_time = datetime(2026, 11, 19, 18, 0, 0)
        line = log_run_summary(
            status="SUCCESS",
            rows_processed=16,
            log_file_path=self.log_path,
            timestamp=fixed_time,
        )

        expected = "2026-11-19 18:00:00 | SUCCESS | 16 rows processed"
        self.assertEqual(line, expected)

        # Verify on-disk file
        content = self.log_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], expected)

    def test_run_log_single_line_error_format(self):
        """Logger must record ERROR with rows processed on a single line."""
        fixed_time = datetime(2026, 11, 19, 18, 0, 0)
        line = log_run_summary(
            status="ERROR",
            rows_processed=0,
            log_file_path=self.log_path,
            error_message="FileNotFoundError: sales_data.csv missing",
            timestamp=fixed_time,
        )

        self.assertIn("2026-11-19 18:00:00", line)
        self.assertIn("ERROR", line)
        self.assertIn("0 rows processed", line)
        self.assertIn("FileNotFoundError", line)

        content = self.log_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        self.assertEqual(len(lines), 1)

    def test_run_log_multiple_runs_appends_one_line_each(self):
        """Subsequent runs must append exactly one new line per run."""
        log_run_summary("SUCCESS", 16, log_file_path=self.log_path, timestamp=datetime(2026, 11, 19, 18, 0, 0))
        log_run_summary("SUCCESS", 16, log_file_path=self.log_path, timestamp=datetime(2026, 11, 19, 18, 5, 0))
        log_run_summary("ERROR", 10, log_file_path=self.log_path, error_message="SMTP timeout", timestamp=datetime(2026, 11, 19, 18, 10, 0))

        content = self.log_path.read_text(encoding="utf-8")
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)

        self.assertTrue(lines[0].endswith("16 rows processed"))
        self.assertTrue(lines[1].endswith("16 rows processed"))
        self.assertIn("SMTP timeout", lines[2])

    def test_pipeline_dry_run_records_in_run_log(self):
        """Running the full pipeline in dry-run mode creates an audit line in run_log.txt."""
        res = run_sales_report_pipeline(
            csv_path=self.csv_path,
            dry_run=True,
            run_log_path=self.log_path,
        )
        self.assertEqual(res["rows_processed"], 10)

        content = self.log_path.read_text(encoding="utf-8")
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn("SUCCESS", lines[0])
        self.assertIn("10 rows processed", lines[0])


if __name__ == "__main__":
    unittest.main()
