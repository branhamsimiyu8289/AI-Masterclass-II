"""
Zawadi Mini-Mart & Provisions - Automated Daily Sales Reporter
==============================================================
Turnkey automated sales reporting and inventory restock monitor.
Designed for retail shop owners in Nairobi (Westlands, Kilimani, Ngong Rd).

Calculates the 4 core business metrics:
  1. Total Daily Revenue (KES)
  2. Number of Transactions (Customer Footfall)
  3. Top-Selling Item (Volume & Revenue)
  4. Restock Level Flag (Threshold Alert System)

Logs every run to `run_log.txt` on a single line:
  Format: <YYYY-MM-DD> <HH:MM:SS> | <STATUS> | <N> rows processed

Scheduled for automatic hands-free dispatch every evening at 6:00 PM (18:00 EAT)
via Windows Task Scheduler or Linux/macOS Cron.
"""

from __future__ import annotations

import argparse
import csv
import html
import logging
import os
import smtplib
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# -----------------------------------------------------------------------------
# Detailed Application Logging (sales_reporter.log)
# -----------------------------------------------------------------------------
APP_LOG_FILE = BASE_DIR / "sales_reporter.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(APP_LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("SalesReporter")


# -----------------------------------------------------------------------------
# Environment & Configuration Loader
# -----------------------------------------------------------------------------
def load_environment(env_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Load environment variables from .env file.
    Searches provided path, script directory, current directory, and Day 23 parent.
    """
    candidates = [
        env_path,
        BASE_DIR / ".env",
        Path.cwd() / ".env",
        BASE_DIR.parent / "day-23" / "retail-sales-reporter" / ".env",
    ]

    loaded = False
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            load_dotenv(candidate, override=False)
            logger.info("Loaded environment configuration from: %s", candidate)
            loaded = True
            break

    if not loaded:
        load_dotenv()
        logger.warning("No explicit .env file found; using ambient environment variables.")

    config = {
        "GMAIL_ADDRESS": os.getenv("GMAIL_ADDRESS", "").strip(),
        "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD", "").strip(),
        "REPORT_RECIPIENT": os.getenv("REPORT_RECIPIENT", "").strip() or os.getenv("GMAIL_ADDRESS", "").strip(),
        "SHOP_NAME": os.getenv("SHOP_NAME", "Zawadi Mini-Mart & Provisions").strip(),
        "SHOP_LOCATION": os.getenv("SHOP_LOCATION", "Westlands, Nairobi, Kenya").strip(),
        "REPORT_TIME_EAT": os.getenv("REPORT_TIME_EAT", "18:00").strip(),
        "DEFAULT_RESTOCK_THRESHOLD": os.getenv("DEFAULT_RESTOCK_THRESHOLD", "10").strip(),
    }
    return config


# -----------------------------------------------------------------------------
# Single-Line Audit Logger (run_log.txt)
# -----------------------------------------------------------------------------
def log_run_summary(
    status: str,
    rows_processed: int,
    log_file_path: Optional[Path] = None,
    error_message: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> str:
    """
    Appends exactly ONE line to run_log.txt with the date, time, status,
    and number of rows processed.

    Format:
      YYYY-MM-DD HH:MM:SS | SUCCESS | 16 rows processed
      YYYY-MM-DD HH:MM:SS | ERROR | 0 rows processed - <error details>
    """
    if timestamp is None:
        timestamp = datetime.now()
    if log_file_path is None:
        log_file_path = BASE_DIR / "run_log.txt"
    else:
        log_file_path = Path(log_file_path)

    date_time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    status_str = status.upper().strip()

    line = f"{date_time_str} | {status_str} | {rows_processed} rows processed"
    if error_message:
        sanitized_err = error_message.replace("\r", " ").replace("\n", " ").strip()
        line += f" - {sanitized_err}"

    line += "\n"

    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(line)

    logger.info("Recorded audit entry in %s: %s", log_file_path.name, line.strip())
    return line.strip()


# -----------------------------------------------------------------------------
# CSV Column Mapping & Normalization
# -----------------------------------------------------------------------------
COLUMN_ALIASES = {
    "item_name": ["item_name", "item", "product", "product_name", "description", "item_description"],
    "quantity_sold": ["quantity_sold", "quantity", "qty", "units_sold", "count"],
    "unit_price": ["unit_price", "price", "unit_price_kes", "selling_price", "rate", "cost"],
    "transaction_id": ["transaction_id", "txn_id", "receipt_no", "order_id", "trans_id", "id"],
    "timestamp": ["timestamp", "time", "date_time", "date", "created_at"],
    "category": ["category", "dept", "department", "type"],
    "payment_method": ["payment_method", "payment", "mode", "payment_mode", "channel"],
    "stock_remaining": ["stock_remaining", "stock", "remaining_stock", "current_stock", "balance_stock"],
    "restock_threshold": ["restock_threshold", "restock_level", "min_stock", "minimum_level", "threshold"],
}


def _match_column(headers: List[str], target_key: str) -> Optional[str]:
    """Find the first matching header name for a target logical field."""
    aliases = COLUMN_ALIASES.get(target_key, [])
    header_map = {h.strip().lower(): h for h in headers}
    for alias in aliases:
        if alias in header_map:
            return header_map[alias]
    return None


# -----------------------------------------------------------------------------
# Core Calculation Logic (The 4 Requested Metrics)
# -----------------------------------------------------------------------------
def parse_sales_csv(
    csv_path: Path,
    inventory_reference_path: Optional[Path] = None,
    default_restock_threshold: int = 10,
) -> Dict[str, Any]:
    """
    Reads sales CSV and calculates:
      1. Total Revenue (KES)
      2. Total Number of Transactions
      3. Top-Selling Item (by quantity and revenue)
      4. Restock Level Flag (and list of low-stock items)
      + Number of rows processed
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Sales CSV file not found: {csv_path.resolve()}")

    # Load inventory reference if present
    inventory_catalog: Dict[str, Dict[str, Any]] = {}
    if inventory_reference_path and Path(inventory_reference_path).exists():
        try:
            with open(inventory_reference_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("item_name", "").strip()
                    if name:
                        inventory_catalog[name] = {
                            "category": row.get("category", "General").strip(),
                            "initial_stock": int(row.get("initial_stock", 0) or 0),
                            "restock_threshold": int(row.get("restock_threshold", default_restock_threshold) or default_restock_threshold),
                        }
            logger.info("Loaded reference catalog for %d items from %s", len(inventory_catalog), Path(inventory_reference_path).name)
        except Exception as exc:
            logger.warning("Could not read inventory reference catalog: %s", exc)

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError(f"Sales CSV file '{csv_path.name}' is empty.")

    headers = [h.strip() for h in raw_headers]
    col_item = _match_column(headers, "item_name")
    col_qty = _match_column(headers, "quantity_sold")
    col_price = _match_column(headers, "unit_price")
    col_txn = _match_column(headers, "transaction_id")
    col_time = _match_column(headers, "timestamp")
    col_cat = _match_column(headers, "category")
    col_payment = _match_column(headers, "payment_method")
    col_stock = _match_column(headers, "stock_remaining")
    col_threshold = _match_column(headers, "restock_threshold")

    if not col_item or not col_qty or not col_price:
        raise ValueError(
            f"CSV is missing required sales columns. Found headers: {headers}. "
            f"Needs item name ('{col_item}'), quantity ('{col_qty}'), price ('{col_price}')."
        )

    transactions: List[Dict[str, Any]] = []
    item_aggregates: Dict[str, Dict[str, Any]] = {}
    payment_aggregates: Dict[str, Dict[str, Any]] = {}
    total_revenue: float = 0.0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        dict_reader = csv.DictReader(f)
        row_idx = 0
        for row in dict_reader:
            row_idx += 1
            raw_item = row.get(col_item, "").strip()
            if not raw_item:
                continue

            try:
                qty = int(float(row.get(col_qty, 0)))
                unit_price = float(row.get(col_price, 0.0))
            except (ValueError, TypeError) as conv_err:
                logger.warning("Row %d: Skipping invalid number in item '%s': %s", row_idx, raw_item, conv_err)
                continue

            line_revenue = qty * unit_price
            total_revenue += line_revenue

            txn_id = row.get(col_txn, "").strip() if col_txn else f"TXN-{row_idx:04d}"
            ts_str = row.get(col_time, "").strip() if col_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            category = row.get(col_cat, "").strip() if col_cat else inventory_catalog.get(raw_item, {}).get("category", "Retail")
            payment_mode = row.get(col_payment, "").strip() if col_payment else "Cash"

            # Stock & Threshold resolution
            stock_val = None
            if col_stock and row.get(col_stock, "").strip() != "":
                try:
                    stock_val = int(float(row.get(col_stock)))
                except ValueError:
                    pass

            thresh_val = None
            if col_threshold and row.get(col_threshold, "").strip() != "":
                try:
                    thresh_val = int(float(row.get(col_threshold)))
                except ValueError:
                    pass

            if thresh_val is None:
                thresh_val = inventory_catalog.get(raw_item, {}).get("restock_threshold", default_restock_threshold)

            transactions.append({
                "row_index": row_idx,
                "transaction_id": txn_id,
                "timestamp": ts_str,
                "item_name": raw_item,
                "category": category,
                "quantity": qty,
                "unit_price": unit_price,
                "line_revenue": line_revenue,
                "payment_mode": payment_mode,
                "stock_remaining": stock_val,
                "restock_threshold": thresh_val,
            })

            # Update item aggregate
            if raw_item not in item_aggregates:
                item_aggregates[raw_item] = {
                    "item_name": raw_item,
                    "category": category,
                    "quantity_sold": 0,
                    "total_revenue": 0.0,
                    "unit_price": unit_price,
                    "latest_stock": stock_val,
                    "restock_threshold": thresh_val,
                    "transaction_count": 0,
                }
            item_aggregates[raw_item]["quantity_sold"] += qty
            item_aggregates[raw_item]["total_revenue"] += line_revenue
            item_aggregates[raw_item]["transaction_count"] += 1
            if stock_val is not None:
                item_aggregates[raw_item]["latest_stock"] = stock_val
            if thresh_val is not None:
                item_aggregates[raw_item]["restock_threshold"] = thresh_val

            # Payment channels
            if payment_mode not in payment_aggregates:
                payment_aggregates[payment_mode] = {"count": 0, "revenue": 0.0}
            payment_aggregates[payment_mode]["count"] += 1
            payment_aggregates[payment_mode]["revenue"] += line_revenue

    if not transactions:
        raise ValueError(f"No valid sales transactions found in '{csv_path.name}'.")

    # If stock_remaining wasn't provided in the CSV, check catalog reference
    for item_name, agg in item_aggregates.items():
        if agg["latest_stock"] is None:
            if item_name in inventory_catalog:
                init_stock = inventory_catalog[item_name]["initial_stock"]
                agg["latest_stock"] = max(0, init_stock - agg["quantity_sold"])
                agg["restock_threshold"] = inventory_catalog[item_name]["restock_threshold"]
            else:
                agg["latest_stock"] = max(0, default_restock_threshold + 5 - agg["quantity_sold"])
                agg["restock_threshold"] = default_restock_threshold

    # Metric 1: Total Revenue
    # total_revenue already accumulated

    # Metric 2: Number of Transactions
    unique_txns = len({t["transaction_id"] for t in transactions})
    total_transactions = unique_txns if unique_txns > 0 else len(transactions)

    # Metric 3: Top-Selling Item
    sorted_by_qty = sorted(item_aggregates.values(), key=lambda x: (x["quantity_sold"], x["total_revenue"]), reverse=True)
    top_selling_item_qty = sorted_by_qty[0]

    sorted_by_rev = sorted(item_aggregates.values(), key=lambda x: x["total_revenue"], reverse=True)
    top_selling_item_rev = sorted_by_rev[0]

    # Metric 4: Restock Level Flag
    low_stock_items: List[Dict[str, Any]] = []
    for item_name, agg in item_aggregates.items():
        stock = agg["latest_stock"]
        threshold = agg["restock_threshold"]
        if stock is not None and threshold is not None and stock < threshold:
            deficit = threshold - stock
            low_stock_items.append({
                "item_name": item_name,
                "category": agg["category"],
                "stock_remaining": stock,
                "restock_threshold": threshold,
                "deficit": deficit,
                "units_sold_today": agg["quantity_sold"],
                "urgency": "CRITICAL" if stock <= (threshold // 2) else "WARNING",
            })

    low_stock_items.sort(key=lambda x: (0 if x["urgency"] == "CRITICAL" else 1, -x["deficit"]))
    restock_flag = len(low_stock_items) > 0

    for agg in item_aggregates.values():
        agg["revenue_share"] = (agg["total_revenue"] / total_revenue * 100.0) if total_revenue > 0 else 0.0

    avg_basket = total_revenue / total_transactions if total_transactions > 0 else 0.0

    return {
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "top_selling_item": top_selling_item_qty,
        "top_selling_item_by_rev": top_selling_item_rev,
        "restock_flag": restock_flag,
        "low_stock_items": low_stock_items,
        "item_aggregates": sorted_by_qty,
        "payment_aggregates": payment_aggregates,
        "recent_transactions": transactions[-10:],
        "average_basket": avg_basket,
        "total_items_sold": sum(t["quantity"] for t in transactions),
        "source_csv": csv_path.name,
        "rows_processed": len(transactions),
    }


# -----------------------------------------------------------------------------
# Formatting Helpers & HTML Email Generation
# -----------------------------------------------------------------------------
def format_currency_kes(amount: float) -> str:
    """Format floating point amount to standard KES currency representation."""
    return f"KES {amount:,.2f}"


def build_email_contents(
    metrics: Dict[str, Any],
    shop_info: Dict[str, str],
) -> Tuple[str, str]:
    """
    Constructs both the multipart HTML and plain-text email bodies.
    All 4 core metrics are prominently visible at the top:
      1. Total Revenue
      2. Number of Transactions
      3. Top-Selling Item
      4. Restock Level Flag
    """
    now = datetime.now()
    report_date = now.strftime("%A, %d %B %Y")
    report_time = now.strftime("%I:%M %p EAT")

    total_revenue_kes = format_currency_kes(metrics["total_revenue"])
    total_txns = metrics["total_transactions"]
    top_item = metrics["top_selling_item"]
    top_item_name = top_item["item_name"]
    top_item_qty = top_item["quantity_sold"]
    top_item_rev = format_currency_kes(top_item["total_revenue"])

    has_low_stock = metrics["restock_flag"]
    low_stock_count = len(metrics["low_stock_items"])

    status_color = "#D32F2F" if has_low_stock else "#2E7D32"
    status_bg = "#FFEBEE" if has_low_stock else "#E8F5E9"
    status_text = (
        f"⚠️ RESTOCK REQUIRED ({low_stock_count} item{'s' if low_stock_count != 1 else ''} low)"
        if has_low_stock
        else "✅ ALL STOCKS HEALTHY"
    )

    # Low Stock Table Rows
    low_stock_rows_html = ""
    low_stock_text_lines = []
    if has_low_stock:
        for it in metrics["low_stock_items"]:
            badge_color = "#C62828" if it["urgency"] == "CRITICAL" else "#EF6C00"
            low_stock_rows_html += f"""
            <tr style="border-bottom: 1px solid #FFCDD2;">
                <td style="padding: 10px 12px; font-weight: 600; color: #333333;">{html.escape(it['item_name'])}</td>
                <td style="padding: 10px 12px; color: #666666;">{html.escape(it['category'])}</td>
                <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: #D32F2F;">{it['stock_remaining']}</td>
                <td style="padding: 10px 12px; text-align: center; color: #555555;">{it['restock_threshold']}</td>
                <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: #C62828;">+{it['deficit']} units</td>
                <td style="padding: 10px 12px; text-align: center;">
                    <span style="background: {badge_color}; color: #FFFFFF; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                        {it['urgency']}
                    </span>
                </td>
            </tr>
            """
            low_stock_text_lines.append(
                f"  * {it['item_name']}: {it['stock_remaining']} left (Min: {it['restock_threshold']}) -> Reorder: {it['deficit']} units [{it['urgency']}]"
            )
    else:
        low_stock_rows_html = """
        <tr>
            <td colspan="6" style="padding: 16px; text-align: center; color: #2E7D32; font-weight: 600;">
                All inventoried products are currently above their minimum safety restock levels.
            </td>
        </tr>
        """
        low_stock_text_lines.append("  All products currently meet or exceed safety restock levels.")

    # Product Breakdown Rows
    items_rows_html = ""
    for agg in metrics["item_aggregates"]:
        rev_str = format_currency_kes(agg["total_revenue"])
        price_str = format_currency_kes(agg["unit_price"])
        stock_badge = (
            f"<span style='color: #D32F2F; font-weight: bold;'>{agg['latest_stock']} (Low!)</span>"
            if agg["latest_stock"] is not None and agg["latest_stock"] < agg["restock_threshold"]
            else f"<span style='color: #2E7D32;'>{agg['latest_stock']}</span>"
        )
        items_rows_html += f"""
        <tr style="border-bottom: 1px solid #E0E0E0;">
            <td style="padding: 10px 12px; color: #222222; font-weight: 500;">{html.escape(agg['item_name'])}</td>
            <td style="padding: 10px 12px; color: #666666;">{html.escape(agg['category'])}</td>
            <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #1565C0;">{agg['quantity_sold']}</td>
            <td style="padding: 10px 12px; text-align: right; color: #555555;">{price_str}</td>
            <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #2E7D32;">{rev_str}</td>
            <td style="padding: 10px 12px; text-align: right; color: #555555;">{agg['revenue_share']:.1f}%</td>
            <td style="padding: 10px 12px; text-align: center;">{stock_badge}</td>
        </tr>
        """

    # Payment Breakdown Badges
    payment_badges_html = ""
    for channel, pdata in metrics["payment_aggregates"].items():
        channel_name = html.escape(channel)
        channel_rev = format_currency_kes(pdata["revenue"])
        payment_badges_html += f"""
        <div style="display: inline-block; background: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 6px; padding: 10px 16px; margin: 4px 8px 4px 0;">
            <span style="font-size: 12px; color: #6B7280; text-transform: uppercase; font-weight: 600; display: block;">{channel_name}</span>
            <span style="font-size: 16px; color: #111827; font-weight: 700;">{channel_rev}</span>
            <span style="font-size: 12px; color: #9CA3AF; margin-left: 4px;">({pdata['count']} txns)</span>
        </div>
        """

    # Responsive HTML Container
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Sales Summary - {html.escape(shop_info['SHOP_NAME'])}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F3F4F6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1F2937;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F3F4F6; padding: 24px 12px;">
        <tr>
            <td align="center">
                <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width: 680px; width: 100%; background-color: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">

                    <!-- Header Banner -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%); padding: 32px 28px; text-align: left;">
                            <span style="background: #E0F2FE; color: #0369A1; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.8px; display: inline-block;">
                                Daily Executive Summary &bull; Automated 6:00 PM
                            </span>
                            <h1 style="color: #FFFFFF; font-size: 24px; font-weight: 800; margin: 12px 0 6px 0; line-height: 1.2;">
                                {html.escape(shop_info['SHOP_NAME'])}
                            </h1>
                            <p style="color: #CBD5E1; font-size: 13px; margin: 0; line-height: 1.4;">
                                📍 {html.escape(shop_info['SHOP_LOCATION'])} &nbsp;|&nbsp; 📅 {report_date} &nbsp;|&nbsp; ⏰ Dispatched {report_time}
                            </p>
                        </td>
                    </tr>

                    <!-- Content Area -->
                    <tr>
                        <td style="padding: 28px;">

                            <!-- SECTION: The 4 Key Metrics Cards -->
                            <h2 style="font-size: 16px; font-weight: 700; color: #111827; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 16px 0;">
                                📊 Key Performance Metrics
                            </h2>

                            <!-- 2x2 Grid of Cards -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <!-- Metric 1: Total Revenue -->
                                    <td width="48%" style="padding: 0 8px 16px 0; vertical-align: top;">
                                        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 18px; height: 100%;">
                                            <div style="font-size: 12px; font-weight: 700; color: #15803D; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                                                💰 1. Total Daily Revenue
                                            </div>
                                            <div style="font-size: 26px; font-weight: 800; color: #166534; line-height: 1.1;">
                                                {total_revenue_kes}
                                            </div>
                                            <div style="font-size: 12px; color: #4B5563; margin-top: 6px;">
                                                Avg Basket: <b>{format_currency_kes(metrics['average_basket'])}</b>
                                            </div>
                                        </div>
                                    </td>

                                    <!-- Metric 2: Number of Transactions -->
                                    <td width="48%" style="padding: 0 0 16px 8px; vertical-align: top;">
                                        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 18px; height: 100%;">
                                            <div style="font-size: 12px; font-weight: 700; color: #1D4ED8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                                                🧾 2. Total Transactions
                                            </div>
                                            <div style="font-size: 26px; font-weight: 800; color: #1E40AF; line-height: 1.1;">
                                                {total_txns} <span style="font-size: 14px; font-weight: 600; color: #3B82F6;">sales</span>
                                            </div>
                                            <div style="font-size: 12px; color: #4B5563; margin-top: 6px;">
                                                Total Units Sold: <b>{metrics['total_items_sold']} items</b>
                                            </div>
                                        </div>
                                    </td>
                                </tr>

                                <tr>
                                    <!-- Metric 3: Top-Selling Item -->
                                    <td width="48%" style="padding: 0 8px 0 0; vertical-align: top;">
                                        <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 18px; height: 100%;">
                                            <div style="font-size: 12px; font-weight: 700; color: #B45309; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                                                🏆 3. Top-Selling Item
                                            </div>
                                            <div style="font-size: 17px; font-weight: 800; color: #92400E; line-height: 1.2;">
                                                {html.escape(top_item_name)}
                                            </div>
                                            <div style="font-size: 12px; color: #78350F; margin-top: 6px;">
                                                <b>{top_item_qty} units</b> sold &nbsp;|&nbsp; <b>{top_item_rev}</b> rev
                                            </div>
                                        </div>
                                    </td>

                                    <!-- Metric 4: Restock Level Flag -->
                                    <td width="48%" style="padding: 0 0 0 8px; vertical-align: top;">
                                        <div style="background: {status_bg}; border: 1px solid {'#FECACA' if has_low_stock else '#BBF7D0'}; border-radius: 8px; padding: 18px; height: 100%;">
                                            <div style="font-size: 12px; font-weight: 700; color: {status_color}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                                                ⚠️ 4. Restock Alert Flag
                                            </div>
                                            <div style="font-size: 16px; font-weight: 800; color: {status_color}; line-height: 1.2;">
                                                {status_text}
                                            </div>
                                            <div style="font-size: 12px; color: #4B5563; margin-top: 6px;">
                                                {"Immediate distributor order advised" if has_low_stock else "Inventory reserves fully covered"}
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            </table>

                            <!-- SECTION: Restock Alert Table -->
                            {f'''
                            <div style="background: #FFF5F5; border-left: 4px solid #D32F2F; border-radius: 6px; padding: 16px; margin-bottom: 28px;">
                                <h3 style="margin: 0 0 8px 0; font-size: 15px; color: #991B1B; font-weight: 700;">
                                    🚨 Restock Action Required: {low_stock_count} Product{'s' if low_stock_count != 1 else ''} Below Threshold
                                </h3>
                                <p style="margin: 0 0 12px 0; font-size: 12px; color: #7F1D1D;">
                                    The following products fell below their safety reorder thresholds today. Replenishment should be placed before opening tomorrow.
                                </p>
                                <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background: #FFFFFF; border-radius: 6px; overflow: hidden; font-size: 12px; border: 1px solid #FECACA;">
                                    <thead>
                                        <tr style="background: #FEE2E2; color: #991B1B; text-align: left; font-weight: 700;">
                                            <th style="padding: 10px 12px;">Item Name</th>
                                            <th style="padding: 10px 12px;">Category</th>
                                            <th style="padding: 10px 12px; text-align: center;">Current Stock</th>
                                            <th style="padding: 10px 12px; text-align: center;">Min Threshold</th>
                                            <th style="padding: 10px 12px; text-align: center;">Reorder Needed</th>
                                            <th style="padding: 10px 12px; text-align: center;">Priority</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {low_stock_rows_html}
                                    </tbody>
                                </table>
                            </div>
                            ''' if has_low_stock else ''}

                            <!-- SECTION: Payment Breakdown -->
                            <div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                                <div style="font-size: 13px; font-weight: 700; color: #374151; margin-bottom: 10px; text-transform: uppercase;">
                                    💳 Settlement Channels (M-Pesa vs Cash)
                                </div>
                                <div>
                                    {payment_badges_html}
                                </div>
                            </div>

                            <!-- SECTION: Detailed Product Sales Breakdown -->
                            <h3 style="font-size: 15px; font-weight: 700; color: #111827; margin: 0 0 12px 0;">
                                📦 Full Daily Item Breakdown ({len(metrics['item_aggregates'])} items, {metrics['rows_processed']} rows)
                            </h3>
                            <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background: #FFFFFF; border-radius: 8px; overflow: hidden; font-size: 12px; border: 1px solid #E5E7EB; margin-bottom: 24px;">
                                <thead>
                                    <tr style="background: #1F2937; color: #FFFFFF; font-weight: 700; text-align: left;">
                                        <th style="padding: 10px 12px;">Product</th>
                                        <th style="padding: 10px 12px;">Category</th>
                                        <th style="padding: 10px 12px; text-align: right;">Qty Sold</th>
                                        <th style="padding: 10px 12px; text-align: right;">Unit Price</th>
                                        <th style="padding: 10px 12px; text-align: right;">Total Revenue</th>
                                        <th style="padding: 10px 12px; text-align: right;">Share</th>
                                        <th style="padding: 10px 12px; text-align: center;">Stock Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items_rows_html}
                                </tbody>
                            </table>

                            <!-- Audit & System Notes -->
                            <div style="font-size: 11px; color: #6B7280; line-height: 1.5; border-top: 1px solid #E5E7EB; padding-top: 16px;">
                                <b>Data Source:</b> Processed {metrics['rows_processed']} transactions from daily cashier log <code>{html.escape(metrics['source_csv'])}</code>.<br>
                                <b>Automation Schedule:</b> Scheduled daily execution at 18:00 East Africa Time via Task Scheduler / Cron.<br>
                                <b>Audit Status:</b> Automated report delivered via Gmail SMTP SSL. Log entry written to <code>run_log.txt</code>.
                            </div>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #F9FAFB; border-top: 1px solid #E5E7EB; padding: 20px 28px; text-align: center;">
                            <p style="font-size: 12px; color: #6B7280; margin: 0 0 4px 0;">
                                <b>{html.escape(shop_info['SHOP_NAME'])}</b> &bull; Retail Sales Automation System
                            </p>
                            <p style="font-size: 11px; color: #9CA3AF; margin: 0;">
                                Hands-Free Automated Reporting &bull; Nairobi, Kenya
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    # Plain-Text Fallback
    plain_text = f"""===================================================================
{shop_info['SHOP_NAME']} - DAILY SALES SUMMARY
===================================================================
Location: {shop_info['SHOP_LOCATION']}
Date:     {report_date}
Time:     {report_time}
Source:   {metrics['source_csv']} ({metrics['rows_processed']} rows processed)

-------------------------------------------------------------------
CORE EXECUTIVE METRICS (THE 4 KEY INDICATORS):
-------------------------------------------------------------------
1. TOTAL REVENUE:          {total_revenue_kes}
2. NUMBER OF TRANSACTIONS: {total_txns} orders (Avg basket: {format_currency_kes(metrics['average_basket'])})
3. TOP-SELLING ITEM:       {top_item_name}
                           ({top_item_qty} units sold, generating {top_item_rev})
4. RESTOCK LEVEL FLAG:     {status_text}

-------------------------------------------------------------------
RESTOCK STATUS & INVENTORY ALERTS:
-------------------------------------------------------------------
"""
    plain_text += "\n".join(low_stock_text_lines) + "\n\n"

    plain_text += "-------------------------------------------------------------------\n"
    plain_text += "PAYMENT CHANNEL BREAKDOWN:\n"
    for ch, p in metrics["payment_aggregates"].items():
        plain_text += f"  - {ch}: {format_currency_kes(p['revenue'])} ({p['count']} txns)\n"

    plain_text += "\n-------------------------------------------------------------------\n"
    plain_text += "TOP PRODUCTS BY REVENUE:\n"
    for agg in metrics["item_aggregates"][:8]:
        plain_text += f"  * {agg['item_name']}: {agg['quantity_sold']} units @ {format_currency_kes(agg['unit_price'])} = {format_currency_kes(agg['total_revenue'])} ({agg['revenue_share']:.1f}% share, Stock: {agg['latest_stock']})\n"

    plain_text += "\n===================================================================\n"
    plain_text += f"Generated automatically by scheduled runner. Logged to run_log.txt.\n"

    return html_body, plain_text


# -----------------------------------------------------------------------------
# Console Output Formatter
# -----------------------------------------------------------------------------
def print_console_summary(shop_name: str, metrics: Dict[str, Any]):
    """Pretty prints the 4 core metrics to stdout for terminal users."""
    print("\n" + "=" * 65)
    print(f" {shop_name} - DAILY SALES SUMMARY")
    print("=" * 65)
    print(f"1. Total Revenue:         {format_currency_kes(metrics['total_revenue'])}")
    print(f"2. Total Transactions:    {metrics['total_transactions']} orders ({metrics['rows_processed']} rows processed)")
    top = metrics['top_selling_item']
    print(f"3. Top-Selling Item:      {top['item_name']} ({top['quantity_sold']} units, {format_currency_kes(top['total_revenue'])})")
    status_label = "⚠️ ALERT: Low stock detected!" if metrics['restock_flag'] else "✅ All stock levels healthy"
    print(f"4. Restock Level Flag:    {status_label}")
    if metrics["restock_flag"]:
        print("\n   Low Stock Items:")
        for item in metrics["low_stock_items"]:
            print(f"     - {item['item_name']}: {item['stock_remaining']} left (min {item['restock_threshold']}, need +{item['deficit']}) [{item['urgency']}]")
    print("=" * 65)


# -----------------------------------------------------------------------------
# Email Dispatcher via Gmail SMTP
# -----------------------------------------------------------------------------
def send_email_via_gmail_smtp(
    sender_email: str,
    app_password: str,
    recipient_email: str,
    subject: str,
    html_content: str,
    plain_content: str,
) -> bool:
    """
    Sends multipart MIME email via Google SMTP SSL on port 465.
    Falls back to port 587 STARTTLS if port 465 is blocked by network firewalls.
    """
    if not sender_email or not app_password:
        raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be configured in environment.")

    clean_password = app_password.replace(" ", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Retail Sales Reports <{sender_email}>"
    msg["To"] = recipient_email

    part1 = MIMEText(plain_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    logger.info("Connecting to Gmail SMTP to send report to: %s...", recipient_email)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender_email, clean_password)
            server.send_message(msg)
            logger.info("Email successfully sent via SMTP_SSL (port 465) to %s", recipient_email)
            return True
    except Exception as ssl_err:
        logger.warning("SMTP_SSL (465) failed (%s); attempting STARTTLS on port 587...", ssl_err)
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender_email, clean_password)
                server.send_message(msg)
                logger.info("Email successfully sent via STARTTLS (port 587) to %s", recipient_email)
                return True
        except Exception as starttls_err:
            logger.error("Failed to send email via both SSL and STARTTLS: %s", starttls_err)
            raise


# -----------------------------------------------------------------------------
# Pipeline Controller with Single-Line run_log.txt Audit Trail
# -----------------------------------------------------------------------------
def run_sales_report_pipeline(
    csv_path: Optional[Path] = None,
    inventory_reference: Optional[Path] = None,
    recipient_override: Optional[str] = None,
    dry_run: bool = False,
    preview_path: Optional[Path] = None,
    env_path: Optional[Path] = None,
    run_log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes the end-to-end sales summary pipeline:
      1. Load environment and shop metadata
      2. Parse CSV and compute metrics
      3. Render HTML and text reports
      4. Save local preview if requested
      5. Send email via Gmail SMTP
      6. Writes exactly ONE line to run_log.txt on completion or failure.
    """
    if csv_path is None:
        csv_path = BASE_DIR / "sales_data.csv"
    else:
        csv_path = Path(csv_path)

    if inventory_reference is None:
        inv_candidate = BASE_DIR / "inventory_reference.csv"
        inventory_reference = inv_candidate if inv_candidate.exists() else None
    else:
        inventory_reference = Path(inventory_reference) if inventory_reference else None

    if run_log_path is None:
        run_log_path = BASE_DIR / "run_log.txt"
    else:
        run_log_path = Path(run_log_path)

    rows_processed = 0

    try:
        config = load_environment(env_path)
        default_thresh = int(config.get("DEFAULT_RESTOCK_THRESHOLD", "10") or 10)

        # 1. Parse CSV
        logger.info("Reading sales CSV from: %s", csv_path.resolve())
        metrics = parse_sales_csv(
            csv_path=csv_path,
            inventory_reference_path=inventory_reference,
            default_restock_threshold=default_thresh,
        )
        rows_processed = metrics["rows_processed"]

        # 2. Build email content
        html_body, plain_text = build_email_contents(metrics, config)

        if preview_path:
            Path(preview_path).write_text(html_body, encoding="utf-8")
            logger.info("HTML preview saved to: %s", Path(preview_path).resolve())

        # Formulate subject line
        date_str = datetime.now().strftime("%Y-%m-%d")
        restock_tag = " [⚠️ RESTOCK NEEDED]" if metrics["restock_flag"] else ""
        subject = f"📊 Daily Sales Summary - {config['SHOP_NAME']} ({date_str}) - {format_currency_kes(metrics['total_revenue'])}{restock_tag}"

        recipient = recipient_override or config["REPORT_RECIPIENT"]
        sender = config["GMAIL_ADDRESS"]
        app_pw = config["GMAIL_APP_PASSWORD"]

        # 3. Print Console Summary
        print_console_summary(config["SHOP_NAME"], metrics)

        if dry_run:
            logger.info("[DRY-RUN] Email dispatch skipped. Metrics calculated successfully.")
            log_run_summary(
                status="SUCCESS",
                rows_processed=rows_processed,
                log_file_path=run_log_path,
            )
            return {
                "metrics": metrics,
                "subject": subject,
                "recipient": recipient,
                "delivered": False,
                "dry_run": True,
                "rows_processed": rows_processed,
            }

        # 4. Dispatch Email
        if not sender or not app_pw:
            raise ValueError("Cannot send email: GMAIL_ADDRESS or GMAIL_APP_PASSWORD is not set in .env")

        send_email_via_gmail_smtp(
            sender_email=sender,
            app_password=app_pw,
            recipient_email=recipient,
            subject=subject,
            html_content=html_body,
            plain_content=plain_text,
        )

        logger.info("Report dispatched successfully to: %s", recipient)

        # 5. Record SUCCESS in run_log.txt
        log_run_summary(
            status="SUCCESS",
            rows_processed=rows_processed,
            log_file_path=run_log_path,
        )

        return {
            "metrics": metrics,
            "subject": subject,
            "recipient": recipient,
            "delivered": True,
            "dry_run": False,
            "rows_processed": rows_processed,
        }

    except Exception as exc:
        logger.error("Report pipeline encountered an error: %s", exc, exc_info=True)
        # Record ERROR in run_log.txt
        log_run_summary(
            status="ERROR",
            rows_processed=rows_processed,
            log_file_path=run_log_path,
            error_message=f"{type(exc).__name__}: {exc}",
        )
        raise


# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Automated Daily Retail Sales Reporter & Inventory Low-Stock Alert System."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to sales CSV file (default: sales_data.csv).",
    )
    parser.add_argument(
        "--inventory",
        type=str,
        default=None,
        help="Path to inventory reference CSV (default: inventory_reference.csv).",
    )
    parser.add_argument(
        "--to",
        type=str,
        default=None,
        help="Override recipient email address.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process CSV and calculate metrics without sending live email.",
    )
    parser.add_argument(
        "--preview",
        type=str,
        default="last_report.html",
        help="Filename to save HTML preview (default: last_report.html).",
    )
    parser.add_argument(
        "--run-log",
        type=str,
        default=None,
        help="Path to single-line run log (default: run_log.txt).",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Path to custom .env file.",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run report immediately (default).",
    )

    args = parser.parse_args()

    csv_file = Path(args.csv) if args.csv and Path(args.csv).is_absolute() else (BASE_DIR / args.csv if args.csv else BASE_DIR / "sales_data.csv")
    inv_file = Path(args.inventory) if args.inventory and Path(args.inventory).is_absolute() else (BASE_DIR / args.inventory if args.inventory else BASE_DIR / "inventory_reference.csv")
    preview_file = Path(args.preview) if Path(args.preview).is_absolute() else BASE_DIR / args.preview
    run_log_file = Path(args.run_log) if args.run_log and Path(args.run_log).is_absolute() else (BASE_DIR / args.run_log if args.run_log else BASE_DIR / "run_log.txt")
    env_file = Path(args.env) if args.env and Path(args.env).is_absolute() else (BASE_DIR / args.env if args.env else None)

    if not inv_file.exists():
        inv_file = None

    run_sales_report_pipeline(
        csv_path=csv_file,
        inventory_reference=inv_file,
        recipient_override=args.to,
        dry_run=args.dry_run,
        preview_path=preview_file,
        env_path=env_file,
        run_log_path=run_log_file,
    )


if __name__ == "__main__":
    main()
