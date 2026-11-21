"""
Unit and Integration Test Suite for Invoice Reminder Script
Validates column parsing, date handling, payment status, tone tier escalations,
email formatting, outbox file generation, and dry-run safety.
"""

import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

# Target module
import invoice_reminder
from invoice_reminder import (
    normalize_string,
    find_column_name,
    parse_currency_amount,
    parse_date,
    is_invoice_paid,
    determine_tone_tier,
    draft_polite_reminder,
    process_invoice_reminders,
    sanitize_filename
)


class TestInvoiceReminder(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.outbox_dir = Path(self.test_dir) / "Outbox"
        self.ref_date = date(2026, 11, 21)
        self.sample_config = {
            "business_name": "Test Agency Ltd",
            "sender_name": "Test Sender",
            "sender_title": "Finance Lead",
            "sender_email": "billing@testagency.com",
            "sender_phone": "+254 700 000 000",
            "mpesa_paybill": "123456",
            "mpesa_account": "[InvoiceID] (or Client Name)",
            "bank_name": "Equity Bank",
            "bank_account_name": "Test Agency Ltd",
            "bank_account_number": "1234567890",
            "bank_branch": "Westlands",
            "default_excel_file": "invoices.xlsx",
            "outbox_dir": str(self.outbox_dir),
            "grace_period_days": 0
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_normalize_string(self):
        self.assertEqual(normalize_string("  Client Name  "), "client name")
        self.assertEqual(normalize_string(None), "")
        self.assertEqual(normalize_string(12345), "12345")

    def test_find_column_name(self):
        available = ["Client", "Invoice Amount", "Due Date", "Paid (Yes/No)"]
        self.assertEqual(find_column_name(available, "client_name"), "Client")
        self.assertEqual(find_column_name(available, "invoice_amount"), "Invoice Amount")
        self.assertEqual(find_column_name(available, "due_date"), "Due Date")
        self.assertEqual(find_column_name(available, "paid"), "Paid (Yes/No)")

        # Alternate synonyms
        available_alt = ["Customer Name", "Total Due", "Deadline", "Payment Status"]
        self.assertEqual(find_column_name(available_alt, "client_name"), "Customer Name")
        self.assertEqual(find_column_name(available_alt, "invoice_amount"), "Total Due")
        self.assertEqual(find_column_name(available_alt, "due_date"), "Deadline")
        self.assertEqual(find_column_name(available_alt, "paid"), "Payment Status")

    def test_parse_currency_amount(self):
        self.assertEqual(parse_currency_amount(45000), 45000.0)
        self.assertEqual(parse_currency_amount("45,000.50"), 45000.50)
        self.assertEqual(parse_currency_amount("KES 18,500"), 18500.0)
        self.assertEqual(parse_currency_amount("Ksh 92,000.00"), 92000.0)
        self.assertEqual(parse_currency_amount(None), 0.0)
        self.assertEqual(parse_currency_amount("invalid"), 0.0)

    def test_parse_date(self):
        expected = date(2026, 11, 15)
        self.assertEqual(parse_date("2026-11-15"), expected)
        self.assertEqual(parse_date("15/11/2026"), expected)
        self.assertEqual(parse_date("11/15/2026"), expected)
        self.assertEqual(parse_date("2026/11/15"), expected)
        self.assertEqual(parse_date(expected), expected)
        self.assertIsNone(parse_date(None))
        self.assertIsNone(parse_date("not-a-date"))

    def test_is_invoice_paid(self):
        # Paid truthy values
        self.assertTrue(is_invoice_paid("Yes"))
        self.assertTrue(is_invoice_paid("yes"))
        self.assertTrue(is_invoice_paid("Y"))
        self.assertTrue(is_invoice_paid("paid"))
        self.assertTrue(is_invoice_paid("settled"))
        self.assertTrue(is_invoice_paid("true"))
        self.assertTrue(is_invoice_paid("1"))

        # Unpaid falsy values
        self.assertFalse(is_invoice_paid("No"))
        self.assertFalse(is_invoice_paid("no"))
        self.assertFalse(is_invoice_paid("N"))
        self.assertFalse(is_invoice_paid("unpaid"))
        self.assertFalse(is_invoice_paid("pending"))
        self.assertFalse(is_invoice_paid("false"))
        self.assertFalse(is_invoice_paid("0"))
        self.assertFalse(is_invoice_paid(""))
        self.assertFalse(is_invoice_paid(None))

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Acme / Corp * Ltd?"), "Acme_Corp_Ltd")
        self.assertEqual(sanitize_filename("INV-1001:Final"), "INV-1001Final")

    def test_tone_tier_classification(self):
        # Tier 1: 1-7 days overdue
        t1, label1, _ = determine_tone_tier(3)
        self.assertEqual(t1, 1)
        self.assertIn("Friendly", label1)

        t1b, _, _ = determine_tone_tier(7)
        self.assertEqual(t1b, 1)

        # Tier 2: 8-21 days overdue
        t2, label2, _ = determine_tone_tier(8)
        self.assertEqual(t2, 2)
        self.assertIn("Follow-Up", label2)

        t2b, _, _ = determine_tone_tier(21)
        self.assertEqual(t2b, 2)

        # Tier 3: 22+ days overdue
        t3, label3, _ = determine_tone_tier(22)
        self.assertEqual(t3, 3)
        self.assertIn("Urgent", label3)

        t3b, _, _ = determine_tone_tier(45)
        self.assertEqual(t3b, 3)

    def test_draft_polite_reminder_content(self):
        inv = {
            "client_name": "Amani Tech",
            "invoice_number": "INV-777",
            "invoice_amount": 50000.0,
            "due_date": date(2026, 11, 10),
            "client_email": "billing@amanitech.ke",
            "service_description": "API Gateway Deployment"
        }
        draft = draft_polite_reminder(inv, self.sample_config, self.ref_date)
        content = draft["content"]

        # Validate headers
        self.assertIn("TO: Amani Tech <billing@amanitech.ke>", content)
        self.assertIn("INVOICE AMOUNT: KES 50,000.00", content)
        self.assertIn("DUE DATE: 10 November 2026", content)
        self.assertIn("SUBJECT: Follow-Up: Outstanding Invoice INV-777", content)

        # Validate tone & payment details
        self.assertIn("Dear Amani Tech,", content)
        self.assertIn("M-PESA PAYBILL", content)
        self.assertIn("Business Number: 123456", content)
        self.assertIn("INV-777 (or Client Name)", content)
        self.assertIn("Equity Bank", content)
        self.assertIn("Test Sender", content)

    def test_pipeline_csv_processing(self):
        # Create a sample CSV in temporary directory
        csv_path = Path(self.test_dir) / "test_invoices.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(
                "Client Name,Invoice Amount,Due Date,Paid (Yes/No),Invoice Number,Client Email\n"
                "Alpha Corp,25000,2026-11-10,No,INV-001,alpha@corp.ke\n"     # 11 days overdue -> Tier 2
                "Beta Logistics,15000,2026-11-19,No,INV-002,beta@corp.ke\n"   # 2 days overdue -> Tier 1
                "Gamma Retail,40000,2026-11-01,Yes,INV-003,gamma@corp.ke\n"  # Paid -> Skipped
                "Delta Hub,30000,2026-11-28,No,INV-004,delta@corp.ke\n"       # Future -> Skipped
            )

        results = process_invoice_reminders(
            filepath=csv_path,
            outbox_dir=self.outbox_dir,
            reference_date=self.ref_date,
            config=self.sample_config
        )

        self.assertEqual(results["total_scanned"], 4)
        self.assertEqual(results["paid_count"], 1)
        self.assertEqual(results["upcoming_count"], 1)
        self.assertEqual(results["overdue_count"], 2)
        self.assertEqual(results["total_overdue_amount"], 40000.0)

        # Check outbox files
        outbox_files = list(self.outbox_dir.glob("*.txt"))
        self.assertEqual(len(outbox_files), 2)
        file_names = [f.name for f in outbox_files]
        self.assertTrue(any("Alpha_Corp" in name for name in file_names))
        self.assertTrue(any("Beta_Logistics" in name for name in file_names))

    def test_dry_run_mode(self):
        csv_path = Path(self.test_dir) / "test_dry.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(
                "Client Name,Invoice Amount,Due Date,Paid (Yes/No)\n"
                "Dry Client,10000,2026-11-01,No\n"
            )

        results = process_invoice_reminders(
            filepath=csv_path,
            outbox_dir=self.outbox_dir,
            reference_date=self.ref_date,
            dry_run=True,
            config=self.sample_config
        )

        self.assertEqual(results["overdue_count"], 1)
        # In dry run mode, outbox should not have files created
        self.assertFalse(self.outbox_dir.exists())

    def test_missing_required_columns_raises_value_error(self):
        invalid_csv = Path(self.test_dir) / "invalid.csv"
        with open(invalid_csv, "w", encoding="utf-8") as f:
            f.write("Random Col A,Random Col B\nVal1,Val2\n")

        with self.assertRaises(ValueError) as ctx:
            process_invoice_reminders(
                filepath=invalid_csv,
                outbox_dir=self.outbox_dir,
                reference_date=self.ref_date,
                config=self.sample_config
            )
        self.assertIn("missing required columns", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
