"""
Daily Retail Sales Reporter & Low-Stock Alert System
=====================================================
Automated daily sales summary and inventory monitor for retail shop owners.
Calculates total revenue, transaction counts, top-selling items, and checks
stock thresholds, then dispatches an executive HTML email report via Gmail SMTP.

Designed for Nairobi retail dukas, mini-marts, and POS cashier logs.
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

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
LOG_FILE = Path(__file__).with_name("sales_reporter.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("SalesReporter")


# -----------------------------------------------------------------------------
# Configuration Loader
# -----------------------------------------------------------------------------
def load_environment(env_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Load environment variables from .env file.
    Searches current directory, script directory, and parent directory.
    """
    candidates = [
        env_path,
        Path(__file__).with_name(".env"),
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / "email-automation" / ".env",
    ]

    loaded = False
    for candidate in candidates:
        if candidate and candidate.is_file():
            load_dotenv(candidate, override=False)
            logger.info("Loaded environment configuration from: %s", candidate)
            loaded = True
            break

    if not loaded:
        # Still load standard dotenv if present in environment
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
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Sales CSV file not found: {csv_path.resolve()}")

    # Load inventory reference if present (for initial stock / thresholds)
    inventory_catalog: Dict[str, Dict[str, Any]] = {}
    if inventory_reference_path and inventory_reference_path.exists():
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
            logger.info("Loaded reference catalog for %d items from %s", len(inventory_catalog), inventory_reference_path.name)
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
                # Fallback: estimate remaining stock based on standard shop stock buffer
                agg["latest_stock"] = max(0, default_restock_threshold + 5 - agg["quantity_sold"])
                agg["restock_threshold"] = default_restock_threshold

    # Metric 1: Total Revenue
    # total_revenue already calculated

    # Metric 2: Number of Transactions
    # Unique transaction IDs if available, else count of records
    unique_txns = len({t["transaction_id"] for t in transactions})
    total_transactions = unique_txns if unique_txns > 0 else len(transactions)

    # Metric 3: Top-Selling Item
    # Sorted by quantity sold (primary) and revenue (secondary)
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

    # Calculate revenue shares
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
    }


# -----------------------------------------------------------------------------
# HTML Email Generation (Responsive, Executive-Ready)
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

    # Color tokens
    status_color = "#D32F2F" if has_low_stock else "#2E7D32"
    status_bg = "#FFEBEE" if has_low_stock else "#E8F5E9"
    status_text = (
        f"⚠️ RESTOCK REQUIRED ({low_stock_count} item{'s' if low_stock_count != 1 else ''} low)"
        if has_low_stock
        else "✅ ALL STOCKS HEALTHY"
    )

    # ------------------ Low Stock Table Rows ------------------
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

    # ------------------ Product Breakdown Rows ------------------
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

    # ------------------ Payment Breakdown ------------------
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

    # ------------------ HTML Template ------------------
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
                <!-- Main Container -->
                <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width: 680px; width: 100%; background-color: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    
                    <!-- Header Banner -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%); padding: 32px 28px; text-align: left;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <span style="background: #E0F2FE; color: #0369A1; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.8px; display: inline-block;">
                                            Daily Executive Summary
                                        </span>
                                        <h1 style="color: #FFFFFF; font-size: 24px; font-weight: 800; margin: 12px 0 6px 0; line-height: 1.2;">
                                            {html.escape(shop_info['SHOP_NAME'])}
                                        </h1>
                                        <p style="color: #CBD5E1; font-size: 13px; margin: 0; line-height: 1.4;">
                                            📍 {html.escape(shop_info['SHOP_LOCATION'])} &nbsp;|&nbsp; 📅 {report_date} &nbsp;|&nbsp; ⏰ Dispatched {report_time}
                                        </p>
                                    </td>
                                </tr>
                            </table>
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

                            <!-- SECTION: Restock Alert Table (Visible if flag is triggered) -->
                            {f'''
                            <div style="background: #FFF5F5; border-left: 4px solid #D32F2F; border-radius: 6px; padding: 16px; margin-bottom: 28px;">
                                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                    <h3 style="margin: 0; font-size: 15px; color: #991B1B; font-weight: 700;">
                                        🚨 Restock Action Required: {low_stock_count} Product{'s' if low_stock_count != 1 else ''} Below Threshold
                                    </h3>
                                </div>
                                <p style="margin: 0 0 12px 0; font-size: 12px; color: #7F1D1D;">
                                    The following products fell below their safety reorder thresholds today. Stock replenishment should be scheduled before next morning opening.
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
                                📦 Full Daily Item Breakdown ({len(metrics['item_aggregates'])} items)
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
                                <b>Data Source:</b> Processed from daily cashier log <code>{html.escape(metrics['source_csv'])}</code>.<br>
                                <b>Automation Schedule:</b> Scheduled daily execution at 18:00 East Africa Time (GMT+3) upon cashier end-of-shift reconciliation.<br>
                                <b>Audit Status:</b> Automated report delivered via Gmail SMTP SSL.
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
                                Powered by Python SMTP Automation &bull; Nairobi, Kenya
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

    # ------------------ Plain-Text Fallback ------------------
    plain_text = f"""===================================================================
{shop_info['SHOP_NAME']} - DAILY SALES SUMMARY
===================================================================
Location: {shop_info['SHOP_LOCATION']}
Date:     {report_date}
Time:     {report_time}
Source:   {metrics['source_csv']}

-------------------------------------------------------------------
CORE EXECUTIVE METRICS (THE 4 KEY INDICATORS):
-------------------------------------------------------------------
1. TOTAL REVENUE:         {total_revenue_kes}
2. NUMBER OF TRANSACTIONS: {total_txns} orders (Avg basket: {format_currency_kes(metrics['average_basket'])})
3. TOP-SELLING ITEM:      {top_item_name}
                          ({top_item_qty} units sold, generating {top_item_rev})
4. RESTOCK LEVEL FLAG:    {status_text}

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
    plain_text += f"Generated automatically at 6:00 PM EAT. Dispatched to shop owner.\n"

    return html_body, plain_text


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
    Sends a multipart MIME email via Google SMTP SSL on port 465.
    Falls back to port 587 STARTTLS if port 465 is blocked by network firewalls.
    """
    if not sender_email or not app_password:
        raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be configured in environment.")

    clean_password = app_password.replace(" ", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Retail Sales Reports <{sender_email}>"
    msg["To"] = recipient_email

    # Attach plain text first, then HTML as alternative
    part1 = MIMEText(plain_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    logger.info("Connecting to Gmail SMTP to send report to: %s...", recipient_email)

    try:
        # Standard SSL on Port 465
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
# Pipeline Controller
# -----------------------------------------------------------------------------
def run_sales_report_pipeline(
    csv_path: Path,
    inventory_reference: Optional[Path] = None,
    recipient_override: Optional[str] = None,
    dry_run: bool = False,
    preview_path: Optional[Path] = None,
    env_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes the end-to-end sales summary pipeline:
      1. Load environment and shop metadata
      2. Parse CSV and compute metrics
      3. Render HTML and text reports
      4. Save local preview if requested
      5. Send email via Gmail SMTP
    """
    config = load_environment(env_path)
    default_thresh = int(config.get("DEFAULT_RESTOCK_THRESHOLD", "10") or 10)

    # 1. Parse CSV
    logger.info("Reading sales CSV from: %s", csv_path.resolve())
    metrics = parse_sales_csv(
        csv_path=csv_path,
        inventory_reference_path=inventory_reference,
        default_restock_threshold=default_thresh,
    )

    # 2. Build email content
    html_body, plain_text = build_email_contents(metrics, config)

    # Save preview if requested
    if preview_path:
        preview_path.write_text(html_body, encoding="utf-8")
        logger.info("HTML preview saved to: %s", preview_path.resolve())

    # Formulate subject line
    date_str = datetime.now().strftime("%Y-%m-%d")
    restock_tag = " [⚠️ RESTOCK NEEDED]" if metrics["restock_flag"] else ""
    subject = f"📊 Daily Sales Summary - {config['SHOP_NAME']} ({date_str}) - {format_currency_kes(metrics['total_revenue'])}{restock_tag}"

    recipient = recipient_override or config["REPORT_RECIPIENT"]
    sender = config["GMAIL_ADDRESS"]
    app_pw = config["GMAIL_APP_PASSWORD"]

    # 3. Print Console Summary
    print("\n" + "=" * 65)
    print(f" {config['SHOP_NAME']} - DAILY SALES SUMMARY")
    print("=" * 65)
    print(f"1. Total Revenue:         {format_currency_kes(metrics['total_revenue'])}")
    print(f"2. Total Transactions:    {metrics['total_transactions']} orders")
    print(f"3. Top-Selling Item:      {metrics['top_selling_item']['item_name']} ({metrics['top_selling_item']['quantity_sold']} units, {format_currency_kes(metrics['top_selling_item']['total_revenue'])})")
    status_label = "⚠️ ALERT: Low stock detected!" if metrics['restock_flag'] else "✅ All stock levels healthy"
    print(f"4. Restock Level Flag:    {status_label}")
    if metrics["restock_flag"]:
        print("\n   Low Stock Items:")
        for item in metrics["low_stock_items"]:
            print(f"     - {item['item_name']}: {item['stock_remaining']} left (min {item['restock_threshold']}, need +{item['deficit']}) [{item['urgency']}]")
    print("=" * 65)

    if dry_run:
        logger.info("[DRY-RUN] Email dispatch skipped. Metrics calculated successfully.")
        return {
            "metrics": metrics,
            "subject": subject,
            "recipient": recipient,
            "delivered": False,
            "dry_run": True,
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
    return {
        "metrics": metrics,
        "subject": subject,
        "recipient": recipient,
        "delivered": True,
        "dry_run": False,
    }


# -----------------------------------------------------------------------------
# Daily Scheduler at 18:00 (6:00 PM EAT)
# -----------------------------------------------------------------------------
def start_daily_scheduler(
    scheduled_time: str,
    csv_path: Path,
    inventory_reference: Optional[Path] = None,
    recipient_override: Optional[str] = None,
):
    """
    Runs a scheduled background loop that fires daily at 6:00 PM (18:00).
    """
    import schedule

    logger.info("Initializing Daily Sales Reporter Scheduler...")
    logger.info("Target Schedule: Every day at %s (Nairobi EAT)", scheduled_time)
    logger.info("Monitoring CSV: %s", csv_path.resolve())

    def job():
        logger.info("⏰ 6:00 PM Trigger: Starting automated daily report generation...")
        try:
            run_sales_report_pipeline(
                csv_path=csv_path,
                inventory_reference=inventory_reference,
                recipient_override=recipient_override,
            )
            logger.info("✅ Daily report scheduled run completed successfully.")
        except Exception as err:
            logger.error("❌ Scheduled report execution failed: %s", err, exc_info=True)

    schedule.every().day.at(scheduled_time).do(job)
    logger.info("Scheduler active. Waiting for trigger time (%s)... Press Ctrl+C to stop.", scheduled_time)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")


# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Daily Retail Sales Reporter & Low-Stock Alert System for Nairobi Retail Shop Owners."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="sales_data.csv",
        help="Path to the sales CSV file updated by cashier (default: sales_data.csv).",
    )
    parser.add_argument(
        "--inventory",
        type=str,
        default="inventory_reference.csv",
        help="Optional path to reference inventory catalog (default: inventory_reference.csv).",
    )
    parser.add_argument(
        "--to",
        type=str,
        default=None,
        help="Override recipient email address (defaults to REPORT_RECIPIENT or GMAIL_ADDRESS).",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in continuous schedule mode (fires daily at 6:00 PM / 18:00).",
    )
    parser.add_argument(
        "--time",
        type=str,
        default="18:00",
        help="Scheduled time in HH:MM 24hr format (default: 18:00).",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run report immediately (default behavior if --schedule is omitted).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate metrics and render email without sending via SMTP.",
    )
    parser.add_argument(
        "--preview",
        type=str,
        default="last_report.html",
        help="Filename to save the generated HTML email preview for inspection.",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Path to custom .env file.",
    )

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    csv_file = Path(args.csv) if Path(args.csv).is_absolute() else base_dir / args.csv
    inventory_file = Path(args.inventory) if Path(args.inventory).is_absolute() else base_dir / args.inventory
    preview_file = Path(args.preview) if Path(args.preview).is_absolute() else base_dir / args.preview
    env_file = Path(args.env) if args.env else None

    if not inventory_file.exists():
        inventory_file = None

    if args.schedule:
        start_daily_scheduler(
            scheduled_time=args.time,
            csv_path=csv_file,
            inventory_reference=inventory_file,
            recipient_override=args.to,
        )
    else:
        run_sales_report_pipeline(
            csv_path=csv_file,
            inventory_reference=inventory_file,
            recipient_override=args.to,
            dry_run=args.dry_run,
            preview_path=preview_file,
            env_path=env_file,
        )


if __name__ == "__main__":
    main()
