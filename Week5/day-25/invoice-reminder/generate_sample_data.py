"""
Sample Data Generator for Invoice Reminder Script
Generates both 'invoices.xlsx' and 'invoices.csv' featuring realistic
Kenyan freelancer and SME client billing scenarios.
"""

from datetime import date, timedelta
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE_DIR = Path(__file__).resolve().parent

def generate_sample_invoices():
    today = date.today()

    # Column layout strictly includes:
    # 'client name', 'invoice amount', 'due date', 'paid (yes/no)'
    # plus auxiliary helper columns: 'invoice number', 'client email', 'service description'
    headers = [
        "Invoice Number",
        "Client Name",
        "Client Email",
        "Service Description",
        "Invoice Amount",
        "Due Date",
        "Paid (Yes/No)"
    ]

    records = [
        {
            "Invoice Number": "INV-1001",
            "Client Name": "Amani Creative Media",
            "Client Email": "accounts@amanimedia.co.ke",
            "Service Description": "Brand Identity & Web Redesign",
            "Invoice Amount": 45000,
            "Due Date": (today - timedelta(days=12)).isoformat(),
            "Paid (Yes/No)": "No",
            "Scenario": "12 days overdue -> Tier 2 Follow-Up"
        },
        {
            "Invoice Number": "INV-1002",
            "Client Name": "Baraka Logistics Ltd",
            "Client Email": "finance@barakalogistics.com",
            "Service Description": "Fleet GPS Tracking Integration",
            "Invoice Amount": 18500,
            "Due Date": (today - timedelta(days=3)).isoformat(),
            "Paid (Yes/No)": "No",
            "Scenario": "3 days overdue -> Tier 1 Friendly Reminder"
        },
        {
            "Invoice Number": "INV-1003",
            "Client Name": "Nairobi Tech Hub",
            "Client Email": "admin@nairobitechhub.org",
            "Service Description": "Cloud Server Optimization",
            "Invoice Amount": 65000,
            "Due Date": (today + timedelta(days=7)).isoformat(),
            "Paid (Yes/No)": "No",
            "Scenario": "Upcoming (due in 7 days) -> Skipped"
        },
        {
            "Invoice Number": "INV-1004",
            "Client Name": "Safari Haven Tours",
            "Client Email": "billing@safarihaven.co.ke",
            "Service Description": "Booking Portal Maintenance",
            "Invoice Amount": 92000,
            "Due Date": (today - timedelta(days=35)).isoformat(),
            "Paid (Yes/No)": "No",
            "Scenario": "35 days overdue -> Tier 3 Urgent Notice"
        },
        {
            "Invoice Number": "INV-1005",
            "Client Name": "Kilifi Coconut Ventures",
            "Client Email": "info@kilificoconut.co.ke",
            "Service Description": "E-Commerce Checkout Setup",
            "Invoice Amount": 14000,
            "Due Date": (today - timedelta(days=16)).isoformat(),
            "Paid (Yes/No)": "Yes",
            "Scenario": "Past due date, but ALREADY PAID -> Skipped"
        },
        {
            "Invoice Number": "INV-1006",
            "Client Name": "Zawadi Retail Grocers",
            "Client Email": "zawadiretail@gmail.com",
            "Service Description": "POS Inventory Script Deployment",
            "Invoice Amount": 28000,
            "Due Date": (today - timedelta(days=9)).isoformat(),
            "Paid (Yes/No)": "No",
            "Scenario": "9 days overdue -> Tier 2 Follow-Up"
        },
        {
            "Invoice Number": "INV-1007",
            "Client Name": "Mama Mboga Fresh Supply",
            "Client Email": "orders@mamamboga.co.ke",
            "Service Description": "WhatsApp Ordering Bot Setup",
            "Invoice Amount": 12500,
            "Due Date": (today - timedelta(days=1)).isoformat(),
            "Paid (Yes/No)": "Yes",
            "Scenario": "Yesterday's due date, ALREADY PAID -> Skipped"
        },
        {
            "Invoice Number": "INV-1008",
            "Client Name": "Eldoret Grain Millers",
            "Client Email": "accounts@eldoretgrain.co.ke",
            "Service Description": "Automated PDF Report Generator",
            "Invoice Amount": 35000,
            "Due Date": (today + timedelta(days=14)).isoformat(),
            "Paid (Yes/No)": "No",
            "Scenario": "Future invoice (due in 14 days) -> Skipped"
        }
    ]

    # 1. Create formatted Excel workbook (.xlsx)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoices"

    # Header styling
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color="D3D3D3"),
        right=Side(style='thin', color="D3D3D3"),
        top=Side(style='thin', color="D3D3D3"),
        bottom=Side(style='thin', color="D3D3D3")
    )

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # Data rows
    for r_idx, item in enumerate(records, start=2):
        row_vals = [
            item["Invoice Number"],
            item["Client Name"],
            item["Client Email"],
            item["Service Description"],
            item["Invoice Amount"],
            item["Due Date"],
            item["Paid (Yes/No)"]
        ]
        ws.append(row_vals)

        # Style data cells
        for c_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.border = thin_border
            if c_idx == 5:  # Amount
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx == 6:  # Due Date
                cell.alignment = Alignment(horizontal="center")
            elif c_idx == 7:  # Paid
                cell.alignment = Alignment(horizontal="center")
                if str(item["Paid (Yes/No)"]).strip().lower() == "yes":
                    cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    excel_path = BASE_DIR / "invoices.xlsx"
    wb.save(excel_path)
    print(f"[OK] Created Excel sample file: {excel_path} ({len(records)} rows)")

    # 2. Also create CSV version for testing/fallback
    csv_path = BASE_DIR / "invoices.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for item in records:
            row_str = f'"{item["Invoice Number"]}","{item["Client Name"]}","{item["Client Email"]}","{item["Service Description"]}",{item["Invoice Amount"]},"{item["Due Date"]}","{item["Paid (Yes/No)"]}"\n'
            f.write(row_str)
    print(f"[OK] Created CSV sample file:   {csv_path} ({len(records)} rows)")

if __name__ == "__main__":
    generate_sample_invoices()
