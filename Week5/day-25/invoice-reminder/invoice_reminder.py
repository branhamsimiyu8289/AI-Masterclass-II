#!/usr/bin/env python3
"""
===============================================================================
Invoice Reminder Script
===============================================================================
Author: Branham Simiyu (AMERIX AI Masterclass II - Week 5, Day 25)
Client Persona: Kenyan Freelancers & Small Business Owners Chasing Payments
Commercial Setup Value: KES 8,000 - 15,000

Description:
    Reads an Excel sheet (.xlsx/.xls) or CSV file with client invoice data:
    - client name
    - invoice amount
    - due date
    - paid (yes/no)
    
    For every unpaid invoice past its due date, dynamically drafts a polite,
    culturally resonant follow-up email tailored to the overdue duration,
    complete with payment details (M-Pesa & Bank Transfer), and saves it as
    a ready-to-dispatch .txt file in the Outbox/ directory.
===============================================================================
"""

import os
import sys
import re
import argparse
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Third-party dependencies
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Base directory of the script
SCRIPT_DIR = Path(__file__).resolve().parent

# Load environment configuration if available
if load_dotenv:
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

# Setup Logging
LOG_FILE = os.getenv("LOG_FILE", "invoice_reminder.log")
logging.basicConfig(
    filename=str(SCRIPT_DIR / LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_logger = logging.getLogger("console")

# Default Business / Payment Configuration
DEFAULT_CONFIG = {
    "business_name": os.getenv("BUSINESS_NAME", "Simiyu Creative Agency"),
    "sender_name": os.getenv("SENDER_NAME", "Branham Simiyu"),
    "sender_title": os.getenv("SENDER_TITLE", "Lead Consultant / Finance"),
    "sender_email": os.getenv("SENDER_EMAIL", "billing@simiyucreative.co.ke"),
    "sender_phone": os.getenv("SENDER_PHONE", "+254 712 345 678"),
    "mpesa_paybill": os.getenv("MPESA_PAYBILL", "247247"),
    "mpesa_account": os.getenv("MPESA_ACCOUNT", "[InvoiceID] (or Client Name)"),
    "bank_name": os.getenv("BANK_NAME", "Equity Bank Kenya"),
    "bank_account_name": os.getenv("BANK_ACCOUNT_NAME", "Simiyu Creative Agency"),
    "bank_account_number": os.getenv("BANK_ACCOUNT_NUMBER", "0110192837465"),
    "bank_branch": os.getenv("BANK_BRANCH", "Westlands Branch, Nairobi"),
    "default_excel_file": os.getenv("DEFAULT_EXCEL_FILE", "invoices.xlsx"),
    "outbox_dir": os.getenv("OUTBOX_DIR", "Outbox"),
    "grace_period_days": int(os.getenv("GRACE_PERIOD_DAYS", "0"))
}

# Synonyms for flexible column mapping
COLUMN_SYNONYMS = {
    "client_name": [
        "client name", "client", "customer name", "customer", "client_name",
        "company name", "client / company", "account name"
    ],
    "invoice_amount": [
        "invoice amount", "amount", "amount due", "total", "invoice_amount",
        "balance", "sum", "kes amount", "total due"
    ],
    "due_date": [
        "due date", "due_date", "deadline", "date due", "payment due date",
        "due", "expiry date"
    ],
    "paid": [
        "paid (yes/no)", "paid", "is paid", "status", "payment status",
        "paid?", "is_paid", "settled"
    ],
    # Optional metadata
    "invoice_number": [
        "invoice number", "invoice #", "invoice no", "inv #", "invoice_id",
        "invoice id", "invoice", "inv no"
    ],
    "client_email": [
        "client email", "email", "contact email", "email address",
        "recipient email"
    ],
    "service_description": [
        "service description", "service", "description", "details",
        "project", "work description"
    ]
}


def normalize_string(val: Any) -> str:
    """Normalize string by lowercasing and stripping whitespace."""
    if val is None:
        return ""
    return str(val).strip().lower()


def find_column_name(available_cols: List[str], target_key: str) -> Optional[str]:
    """
    Find matching column name from spreadsheet based on known synonyms.
    """
    synonyms = COLUMN_SYNONYMS.get(target_key, [])
    # 1. Exact match (case-insensitive)
    for col in available_cols:
        norm = normalize_string(col)
        if norm in synonyms:
            return col
    
    # 2. Substring match
    for col in available_cols:
        norm = normalize_string(col)
        for syn in synonyms:
            if syn in norm or norm in syn:
                return col
    return None


def parse_currency_amount(val: Any) -> float:
    """
    Clean and convert currency values to float (e.g. 'KES 45,000.00' -> 45000.0).
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    clean_str = str(val).strip()
    # Remove currency prefixes, commas, and spaces
    clean_str = re.sub(r'[^\d.-]', '', clean_str)
    try:
        return float(clean_str)
    except ValueError:
        return 0.0


def parse_date(val: Any) -> Optional[date]:
    """
    Parse a date from datetime, timestamp, or multiple string formats.
    """
    if val is None or pd.isna(val):
        return None
    
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val
    
    val_str = str(val).strip()
    if not val_str:
        return None
    
    # Try common formats
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%b %d, %Y",
        "%B %d, %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
            
    # Try ISO timestamp format with time part
    try:
        return datetime.fromisoformat(val_str.split("T")[0]).date()
    except Exception:
        pass
        
    return None


def is_invoice_paid(val: Any) -> bool:
    """
    Evaluate whether a row indicates that the invoice has been paid.
    Accepts: 'yes', 'y', 'true', '1', 'paid', 'settled', 'complete'.
    """
    norm = normalize_string(val)
    paid_indicators = ["yes", "y", "true", "1", "paid", "settled", "cleared", "closed", "complete"]
    return norm in paid_indicators


def sanitize_filename(name: str) -> str:
    """
    Sanitize string to create safe, cross-platform filenames.
    """
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', "_", clean.strip())
    return clean or "unknown"


def load_spreadsheet_data(filepath: Path) -> List[Dict[str, Any]]:
    """
    Load rows from an Excel (.xlsx/.xls) or CSV file into a list of normalized dictionaries.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Spreadsheet file not found: {filepath}")

    ext = filepath.suffix.lower()
    if ext in [".xlsx", ".xls"]:
        if openpyxl is None and pd is None:
            raise ImportError("Neither 'pandas' nor 'openpyxl' is installed to read Excel files.")
        
        # Read Excel using pandas or openpyxl
        if pd is not None:
            df = pd.read_excel(filepath, engine="openpyxl" if ext == ".xlsx" else None)
            raw_cols = [str(c).strip() for c in df.columns]
            rows = df.to_dict(orient="records")
        else:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb.active
            data = list(ws.iter_rows(values_only=True))
            if not data or len(data) < 2:
                return []
            raw_cols = [str(c).strip() if c is not None else "" for c in data[0]]
            rows = [dict(zip(raw_cols, row)) for row in data[1:]]
    elif ext == ".csv":
        if pd is not None:
            df = pd.read_csv(filepath)
            raw_cols = [str(c).strip() for c in df.columns]
            rows = df.to_dict(orient="records")
        else:
            import csv
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                raw_cols = list(reader.fieldnames or [])
                rows = list(reader)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please provide .xlsx, .xls, or .csv.")

    # Match mandatory columns
    col_client = find_column_name(raw_cols, "client_name")
    col_amount = find_column_name(raw_cols, "invoice_amount")
    col_due_date = find_column_name(raw_cols, "due_date")
    col_paid = find_column_name(raw_cols, "paid")

    # Match optional columns
    col_inv_no = find_column_name(raw_cols, "invoice_number")
    col_email = find_column_name(raw_cols, "client_email")
    col_service = find_column_name(raw_cols, "service_description")

    missing = []
    if not col_client:
        missing.append("client name")
    if not col_amount:
        missing.append("invoice amount")
    if not col_due_date:
        missing.append("due date")
    if not col_paid:
        missing.append("paid (yes/no)")

    if missing:
        raise ValueError(
            f"Spreadsheet '{filepath.name}' is missing required columns: {', '.join(missing)}.\n"
            f"Available columns found: {raw_cols}"
        )

    normalized_rows = []
    for idx, row in enumerate(rows, start=1):
        # Extract values
        client = str(row.get(col_client, "") or "").strip()
        if not client or client.lower() == "nan":
            continue  # Skip blank rows

        amount = parse_currency_amount(row.get(col_amount))
        due_dt = parse_date(row.get(col_due_date))
        paid_flag = is_invoice_paid(row.get(col_paid))

        inv_num = str(row.get(col_inv_no, "") or "").strip() if col_inv_no else ""
        if not inv_num or inv_num.lower() == "nan":
            inv_num = f"INV-REC{idx:03d}"

        email = str(row.get(col_email, "") or "").strip() if col_email else ""
        if email.lower() == "nan":
            email = ""

        service = str(row.get(col_service, "") or "").strip() if col_service else ""
        if service.lower() == "nan":
            service = "Professional Services"

        normalized_rows.append({
            "client_name": client,
            "invoice_amount": amount,
            "due_date": due_dt,
            "is_paid": paid_flag,
            "invoice_number": inv_num,
            "client_email": email,
            "service_description": service,
            "row_number": idx
        })

    return normalized_rows


def determine_tone_tier(days_overdue: int) -> Tuple[int, str, str]:
    """
    Select appropriate tone and subject heading based on days overdue:
    - Tier 1: 1 - 7 days overdue -> Friendly check-in
    - Tier 2: 8 - 21 days overdue -> Standard follow-up
    - Tier 3: 22+ days overdue -> Important overdue notice
    """
    if days_overdue <= 7:
        tier = 1
        tier_label = "Friendly Check-in"
        subject_prefix = "Gentle Reminder: Invoice"
    elif days_overdue <= 21:
        tier = 2
        tier_label = "Standard Follow-Up"
        subject_prefix = "Follow-Up: Outstanding Invoice"
    else:
        tier = 3
        tier_label = "Urgent Notice"
        subject_prefix = "Important Notice: Overdue Invoice"
    
    return tier, tier_label, subject_prefix


def draft_polite_reminder(
    invoice: Dict[str, Any],
    config: Dict[str, Any],
    reference_date: date
) -> Dict[str, Any]:
    """
    Draft a polite, professional, and culturally appropriate follow-up email.
    """
    client_name = invoice["client_name"]
    inv_number = invoice["invoice_number"]
    amount_kes = invoice["invoice_amount"]
    due_date = invoice["due_date"]
    client_email = invoice["client_email"]
    service = invoice.get("service_description", "Professional Services")
    
    days_overdue = (reference_date - due_date).days
    tier, tier_label, subject_prefix = determine_tone_tier(days_overdue)

    # Format currency
    formatted_amount = f"KES {amount_kes:,.2f}"
    formatted_due_date = due_date.strftime("%d %B %Y")
    current_date_str = reference_date.strftime("%d %B %Y")

    # Payment details block
    mpesa_acc = config["mpesa_account"].replace("[InvoiceID]", inv_number).replace("[ClientName]", client_name)
    payment_block = f"""PAYMENT DETAILS:
--------------------------------------------------------------------------------
1. M-PESA PAYBILL
   - Business Number: {config['mpesa_paybill']}
   - Account Number : {mpesa_acc}

2. BANK TRANSFER
   - Bank Name      : {config['bank_name']}
   - Account Name   : {config['bank_account_name']}
   - Account Number : {config['bank_account_number']}
   - Branch         : {config['bank_branch']}
--------------------------------------------------------------------------------"""

    # Subject line
    subject = f"{subject_prefix} {inv_number} ({client_name}) - {config['business_name']}"

    # Email body templates by tier
    if tier == 1:
        # 1-7 days: Warm, assumes good faith / oversight
        body = f"""Dear {client_name},

I hope you are having a productive and pleasant week.

This is a friendly reminder that invoice {inv_number} for {formatted_amount} (regarding: {service}) was due on {formatted_due_date} ({days_overdue} days ago).

We know how quickly time flies and how busy schedules get, so we wanted to gently bring this to your attention in case it slipped past your inbox. If payment has already been initiated, please disregard this note with our warmest thanks.

{payment_block}

If you need another copy of the original invoice or have any questions regarding the deliverables, please reply directly or reach me via WhatsApp/phone at {config['sender_phone']}.

Thank you for your valued partnership!

Warm regards,

{config['sender_name']}
{config['sender_title']}
{config['business_name']}
Phone: {config['sender_phone']}
Email: {config['sender_email']}
"""

    elif tier == 2:
        # 8-21 days: Direct, professional, polite
        body = f"""Dear {client_name},

I hope this email finds you well.

I am writing to follow up on invoice {inv_number} for {formatted_amount} covering {service}, which fell due on {formatted_due_date} and is now {days_overdue} days past due.

To keep our accounts reconciled and ensure uninterrupted service, could you kindly confirm when this payment is scheduled for disbursement? 

{payment_block}

Once payment has been processed, please share the transaction reference (e.g. M-Pesa confirmation code or bank slip) so we can update our ledger and issue your official receipt.

Should you require any clarification or wish to discuss a specific payment arrangement, feel free to reach out to me directly at {config['sender_phone']}.

Thank you for your prompt attention to this matter.

Kind regards,

{config['sender_name']}
{config['sender_title']}
{config['business_name']}
Phone: {config['sender_phone']}
Email: {config['sender_email']}
"""

    else:
        # 22+ days: Urgent, firm, yet respectful and polite
        body = f"""Dear {client_name},

I hope you are well.

I am writing regarding invoice {inv_number} for {formatted_amount} for {service}, which became due on {formatted_due_date} and is now {days_overdue} days past due.

As an independent business, steady cash flow is essential to fulfilling our operational overheads and continuing to deliver quality services. While we value our business relationship and understand unexpected delays happen, this account is now significantly overdue.

We kindly request that you settle the outstanding balance within the next 48 to 72 business hours using the payment methods below:

{payment_block}

If there is a billing discrepancy or an extenuating circumstance preventing payment this week, please contact me immediately today at {config['sender_phone']} or {config['sender_email']} so we can reach an agreeable resolution.

Thank you for prioritizing the settlement of this account.

Sincerely,

{config['sender_name']}
{config['sender_title']}
{config['business_name']}
Phone: {config['sender_phone']}
Email: {config['sender_email']}
"""

    # Structured full email text
    recipient_header = f"{client_name} <{client_email}>" if client_email else client_name
    full_content = f"""TO: {recipient_header}
DATE: {current_date_str}
SUBJECT: {subject}
TIER: Tier {tier} ({tier_label} - {days_overdue} days overdue)
INVOICE AMOUNT: {formatted_amount}
DUE DATE: {formatted_due_date}
================================================================================

{body}"""

    # Filename
    safe_client = sanitize_filename(client_name)
    safe_inv = sanitize_filename(inv_number)
    date_slug = reference_date.strftime("%Y%m%d")
    filename = f"Reminder_{safe_client}_{safe_inv}_{date_slug}.txt"

    return {
        "invoice": invoice,
        "filename": filename,
        "subject": subject,
        "content": full_content,
        "tier": tier,
        "tier_label": tier_label,
        "days_overdue": days_overdue
    }


def process_invoice_reminders(
    filepath: Path,
    outbox_dir: Path,
    reference_date: Optional[date] = None,
    grace_period_days: int = 0,
    dry_run: bool = False,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main processing pipeline:
    1. Loads spreadsheet data.
    2. Identifies unpaid invoices where due_date < (reference_date - grace_period).
    3. Drafts polite emails.
    4. Writes .txt files to Outbox/.
    5. Returns metrics and execution summary.
    """
    cfg = config or DEFAULT_CONFIG
    ref_dt = reference_date or date.today()

    logging.info(f"Starting invoice reminder run for '{filepath.name}' (Ref date: {ref_dt})")
    rows = load_spreadsheet_data(filepath)

    total_scanned = len(rows)
    paid_count = 0
    upcoming_count = 0
    overdue_count = 0
    drafts_created: List[Dict[str, Any]] = []
    skipped_records: List[Dict[str, Any]] = []
    total_overdue_amount = 0.0

    if not dry_run:
        outbox_dir.mkdir(parents=True, exist_ok=True)

    for record in rows:
        client = record["client_name"]
        inv_no = record["invoice_number"]
        amount = record["invoice_amount"]
        due_dt = record["due_date"]
        is_paid = record["is_paid"]

        # Case 1: Already paid
        if is_paid:
            paid_count += 1
            skipped_records.append({
                "client": client,
                "invoice": inv_no,
                "amount": amount,
                "due_date": due_dt,
                "reason": "Paid (Settled)"
            })
            continue

        # Check due date
        if due_dt is None:
            skipped_records.append({
                "client": client,
                "invoice": inv_no,
                "amount": amount,
                "due_date": "N/A",
                "reason": "Missing due date"
            })
            continue

        days_past = (ref_dt - due_dt).days

        # Case 2: Due in future or within grace period
        if days_past <= grace_period_days:
            upcoming_count += 1
            skipped_records.append({
                "client": client,
                "invoice": inv_no,
                "amount": amount,
                "due_date": due_dt,
                "reason": f"Not overdue (Due in {-days_past} days)" if days_past < 0 else "Due today / within grace period"
            })
            continue

        # Case 3: Overdue & Unpaid!
        overdue_count += 1
        total_overdue_amount += amount

        draft = draft_polite_reminder(record, cfg, ref_dt)
        draft_file_path = outbox_dir / draft["filename"]

        if not dry_run:
            with open(draft_file_path, "w", encoding="utf-8") as f:
                f.write(draft["content"])
            logging.info(f"Drafted reminder for {client} ({inv_no}) -> {draft['filename']}")

        draft["file_path"] = draft_file_path
        drafts_created.append(draft)

    # Log single-line summary
    status_str = "SUCCESS" if total_scanned > 0 else "EMPTY"
    log_line = f"{ref_dt} | {status_str} | {total_scanned} scanned | {overdue_count} overdue reminders drafted | KES {total_overdue_amount:,.2f} total overdue"
    logging.info(log_line)

    return {
        "reference_date": ref_dt,
        "total_scanned": total_scanned,
        "paid_count": paid_count,
        "upcoming_count": upcoming_count,
        "overdue_count": overdue_count,
        "total_overdue_amount": total_overdue_amount,
        "drafts": drafts_created,
        "skipped": skipped_records,
        "dry_run": dry_run,
        "outbox_dir": outbox_dir
    }


def print_cli_summary(results: Dict[str, Any], verbose: bool = True):
    """
    Print a clean terminal dashboard with color highlights and table layout.
    """
    ref_dt = results["reference_date"]
    print("=" * 78)
    print(f"  INVOICE REMINDER AUTOMATION SERVICE  --  {ref_dt.strftime('%d %B %Y')}")
    print("=" * 78)
    print(f"  Total Invoices Scanned : {results['total_scanned']}")
    print(f"  - Settled / Paid       : {results['paid_count']}")
    print(f"  - Upcoming / Current   : {results['upcoming_count']}")
    print(f"  - Overdue (Unpaid)     : {results['overdue_count']}")
    print(f"  Total Overdue Balance  : KES {results['total_overdue_amount']:,.2f}")
    if results['dry_run']:
        print("  Mode                   : [DRY RUN - No files created]")
    else:
        print(f"  Outbox Folder          : {results['outbox_dir'].resolve()}")
    print("-" * 78)

    if results["drafts"]:
        print("\n[+] DRAFTED EMAIL REMINDERS (SAVED TO OUTBOX):")
        print(f"{'Client Name':<24} {'Invoice #':<10} {'Amount (KES)':>14} {'Days Late':>10} {'Tone Tier':<16}")
        print("-" * 78)
        for d in results["drafts"]:
            c_name = d["invoice"]["client_name"][:22]
            inv_no = d["invoice"]["invoice_number"]
            amt = f"{d['invoice']['invoice_amount']:,.2f}"
            days = f"+{d['days_overdue']} d"
            tier = f"Tier {d['tier']} ({d['tier_label']})"
            print(f"{c_name:<24} {inv_no:<10} {amt:>14} {days:>10} {tier:<16}")
            if verbose:
                print(f"    --> File: {d['filename']}")
        print("-" * 78)
    else:
        print("\n[OK] No overdue invoices found! All clients are up to date.")

    if verbose and results["skipped"]:
        print("\n[-] SKIPPED INVOICES (UP TO DATE OR NOT OVERDUE):")
        for s in results["skipped"]:
            amt_str = f"KES {s['amount']:,.2f}" if isinstance(s['amount'], (int, float)) else str(s['amount'])
            print(f"  * {s['client']} ({s['invoice']}) - {amt_str} | Status: {s['reason']}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(
        description="Automated Invoice Reminder Script: Reads client invoices and drafts follow-up emails in Outbox/"
    )
    parser.add_argument(
        "-f", "--file",
        default=DEFAULT_CONFIG["default_excel_file"],
        help=f"Path to Excel (.xlsx/.xls) or CSV spreadsheet (default: {DEFAULT_CONFIG['default_excel_file']})"
    )
    parser.add_argument(
        "-o", "--outbox",
        default=DEFAULT_CONFIG["outbox_dir"],
        help=f"Path to Outbox directory for saving drafted emails (default: {DEFAULT_CONFIG['outbox_dir']})"
    )
    parser.add_argument(
        "-d", "--reference-date",
        default=None,
        help="Simulate run with reference date (format: YYYY-MM-DD). Defaults to current date."
    )
    parser.add_argument(
        "-g", "--grace-period",
        type=int,
        default=DEFAULT_CONFIG["grace_period_days"],
        help=f"Grace period days before an invoice is considered overdue (default: {DEFAULT_CONFIG['grace_period_days']})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform calculations and preview drafted emails without creating files in Outbox/"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress detailed console logging"
    )

    args = parser.parse_args()

    # Resolve paths
    input_path = Path(args.file)
    if not input_path.is_absolute():
        input_path = SCRIPT_DIR / input_path

    outbox_path = Path(args.outbox)
    if not outbox_path.is_absolute():
        outbox_path = SCRIPT_DIR / outbox_path

    ref_dt = None
    if args.reference_date:
        try:
            ref_dt = datetime.strptime(args.reference_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.reference_date}'. Please use YYYY-MM-DD.")
            sys.exit(1)

    try:
        results = process_invoice_reminders(
            filepath=input_path,
            outbox_dir=outbox_path,
            reference_date=ref_dt,
            grace_period_days=args.grace_period,
            dry_run=args.dry_run
        )
        if not args.quiet:
            print_cli_summary(results, verbose=not args.quiet)
    except Exception as e:
        logging.error(f"Execution failed: {e}", exc_info=True)
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
