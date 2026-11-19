"""
Unit and Integration Tests for Daily Retail Sales Reporter
"""

import csv
import tempfile
import unittest
from pathlib import Path

from sales_reporter import (
    build_email_contents,
    format_currency_kes,
    parse_sales_csv,
)


class TestSalesReporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "test_sales.csv"

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
            writer.writerow(["TXN-05", "2026-11-19 11:00:00", "Brookside Milk 500ml", "Dairy", 6, 65.0, "M-Pesa", 9, 10])  # Low stock after 2nd sale!
            writer.writerow(["TXN-06", "2026-11-19 12:30:00", "Cooking Oil 1L", "Cooking Oils", 1, 320.0, "M-Pesa", 14, 5])
            writer.writerow(["TXN-07", "2026-11-19 13:15:00", "Indomie Noodles 120g", "Quick Meals", 10, 50.0, "Cash", 50, 20])
            writer.writerow(["TXN-08", "2026-11-19 14:00:00", "Royco Cubes 40s", "Seasoning", 2, 140.0, "Cash", 18, 10])
            writer.writerow(["TXN-09", "2026-11-19 15:20:00", "Ketepa Tea Leaves 250g", "Beverages", 1, 135.0, "M-Pesa", 12, 10])
            writer.writerow(["TXN-10", "2026-11-19 16:45:00", "Omo Washing Powder 500g", "Household", 2, 220.0, "M-Pesa", 4, 10])  # Low stock!

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_total_revenue_calculation(self):
        """Metric 1: Total Revenue must equal sum of (qty * price)."""
        metrics = parse_sales_csv(self.csv_path)
        # Expected calculation:
        # 5*65 + 2*215 + 3*160 + 4*65 + 6*65 + 1*320 + 10*50 + 2*140 + 1*135 + 2*220
        # = 325 + 430 + 480 + 260 + 390 + 320 + 500 + 280 + 135 + 440 = 3560.0
        self.assertAlmostEqual(metrics["total_revenue"], 3560.0, places=2)

    def test_total_transactions_count(self):
        """Metric 2: Number of transactions must match unique transaction records."""
        metrics = parse_sales_csv(self.csv_path)
        self.assertEqual(metrics["total_transactions"], 10)

    def test_top_selling_item_identification(self):
        """Metric 3: Top-selling item by quantity should be Brookside Milk (11 units total across rows)."""
        metrics = parse_sales_csv(self.csv_path)
        top_item = metrics["top_selling_item"]
        self.assertEqual(top_item["item_name"], "Brookside Milk 500ml")
        self.assertEqual(top_item["quantity_sold"], 11)
        self.assertAlmostEqual(top_item["total_revenue"], 11 * 65.0, places=2)

    def test_restock_level_flag_trigger(self):
        """Metric 4: Flag must be True when items drop below threshold."""
        metrics = parse_sales_csv(self.csv_path)
        self.assertTrue(metrics["restock_flag"])
        low_names = [it["item_name"] for it in metrics["low_stock_items"]]
        self.assertIn("Pembe Flour 2kg", low_names)
        self.assertIn("Kabras Sugar 1kg", low_names)
        self.assertIn("Brookside Milk 500ml", low_names)
        self.assertIn("Omo Washing Powder 500g", low_names)

    def test_no_low_stock_flag(self):
        """When all stock is above threshold, restock flag must be False."""
        healthy_csv = Path(self.temp_dir.name) / "healthy_sales.csv"
        with open(healthy_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["item_name", "quantity_sold", "unit_price", "stock_remaining", "restock_threshold"])
            writer.writerow(["Item A", 2, 100.0, 50, 10])
            writer.writerow(["Item B", 1, 200.0, 30, 5])

        metrics = parse_sales_csv(healthy_csv)
        self.assertFalse(metrics["restock_flag"])
        self.assertEqual(len(metrics["low_stock_items"]), 0)

    def test_flexible_column_mapping(self):
        """Parser must work with alternative common column names (e.g. 'item', 'qty', 'price')."""
        alt_csv = Path(self.temp_dir.name) / "alt_sales.csv"
        with open(alt_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["item", "qty", "price"])
            writer.writerow(["Milk 500ml", 3, 60.0])
            writer.writerow(["Bread 400g", 2, 70.0])

        metrics = parse_sales_csv(alt_csv)
        self.assertEqual(metrics["total_transactions"], 2)
        self.assertAlmostEqual(metrics["total_revenue"], 320.0, places=2)
        self.assertEqual(metrics["top_selling_item"]["item_name"], "Milk 500ml")

    def test_html_and_text_report_generation(self):
        """Generated HTML must contain all 4 metrics clearly rendered."""
        metrics = parse_sales_csv(self.csv_path)
        shop_info = {
            "SHOP_NAME": "Test Nairobi Duka",
            "SHOP_LOCATION": "CBD, Nairobi",
        }
        html_body, plain_text = build_email_contents(metrics, shop_info)

        # Check for Metric 1 (Total Revenue)
        self.assertIn("KES 3,560.00", html_body)
        self.assertIn("KES 3,560.00", plain_text)

        # Check for Metric 2 (Transactions)
        self.assertIn("10", html_body)
        self.assertIn("10 orders", plain_text)

        # Check for Metric 3 (Top-Selling Item)
        self.assertIn("Brookside Milk 500ml", html_body)
        self.assertIn("Brookside Milk 500ml", plain_text)

        # Check for Metric 4 (Restock Flag)
        self.assertIn("RESTOCK REQUIRED", html_body)
        self.assertIn("RESTOCK REQUIRED", plain_text)

    def test_empty_csv_error_handling(self):
        """Empty CSV should raise ValueError with friendly message."""
        empty_csv = Path(self.temp_dir.name) / "empty.csv"
        empty_csv.write_text("", encoding="utf-8")
        with self.assertRaises(ValueError):
            parse_sales_csv(empty_csv)


if __name__ == "__main__":
    unittest.main()
