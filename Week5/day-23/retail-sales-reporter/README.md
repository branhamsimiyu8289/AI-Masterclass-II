# Daily Retail Sales Reporter & Low-Stock Alert System
### Automated 6:00 PM Executive Intelligence for Nairobi Retail Shop Owners

An end-to-end Python automation pipeline engineered for retail shop owners, mini-marts, and FMCG dukas across Nairobi (Westlands, Ngong Road, Eastleigh, Kilimani). The system ingests daily cashier sales logs (CSV), computes four core business metrics, monitors inventory safety levels, and delivers a formatted, mobile-responsive HTML summary directly to the owner's email every evening at **6:00 PM East Africa Time (EAT)** via secure Gmail SMTP.

---

## 1. Business Problem Scenario

In Nairobi's retail landscape, independent shop owners often manage multiple locations or are away from the sales floor negotiating with distributors, managing cash flow, or attending to family. Meanwhile, shop cashiers log customer purchases throughout the day using a point-of-sale (POS) terminal, electronic till, or an Excel/CSV spreadsheet.

At the close of the business day (typically 6:00 PM), shop owners face three critical operational bottlenecks:
1. **Blindness to Daily Revenue**: Owners often have to wait until late night or physical reconciliation to know whether the day was profitable.
2. **Stockout Surprises**: Fast-moving consumer goods (e.g. *Pembe Maize Flour*, *Brookside Milk*, *Broadways Bread*, *Kabras Sugar*) sell out without timely notice, causing lost sales the following morning before distributors make deliveries.
3. **Manual Overhead & Cashier Errors**: Calculating daily totals, sorting top sellers, and checking inventory levels by hand is slow and prone to arithmetic mistakes.

### The Automated Solution
This automated pipeline runs at **6:00 PM EAT** (or on-demand). It automatically:
- Ingests the day's updated sales CSV.
- Computes the **four essential operational metrics**.
- Generates an executive-ready, mobile-optimized HTML email with visual KPI badges and alert tables.
- Dispatches the report to the owner's inbox via Gmail SMTP with an encrypted App Password.

---

## 2. The Four Core Metrics

The system calculates and highlights four primary indicators required by retail proprietors:

| Metric | Business Definition | Nairobi Retail Context | Example Output |
|---|---|---|---|
| **1. Total Revenue** | Gross monetary intake across all sales transactions for the day. | Denominated in Kenyan Shillings (`KES`), split by cash and M-Pesa. | `KES 6,590.00` |
| **2. Total Transactions** | Count of individual purchase tickets logged by cashiers. | Measures customer footfall and average transaction basket size. | `16 orders` (Avg Basket: `KES 411.88`) |
| **3. Top-Selling Item** | The inventory product with the highest aggregate unit volume and gross contribution. | Identifies fast-moving consumer demand to optimize shelf placement. | `Brookside Fresh Milk 500ml` (9 units sold, `KES 585.00`) |
| **4. Restock Level Flag** | Automated inventory safety check flagging any item where `stock_remaining < restock_threshold`. | Triggers an immediate reorder notice before suppliers close orders for next-day dispatch. | `⚠️ RESTOCK REQUIRED` (5 items flagged with deficit quantities) |

---

## 3. System Architecture & Workflow

```
 ┌────────────────────────┐
 │   Cashier Till / POS   │
 │ Updates sales_data.csv │
 └───────────┬────────────┘
             │
             ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                sales_reporter.py Pipeline                   │
 │                                                             │
 │  1. Ingestion: Flexible CSV column alias resolver           │
 │  2. Analytics: Revenue, txns, top sellers, low stock filter │
 │  3. Rendering: Responsive HTML + RFC 822 Plain Text         │
 │  4. Schedule:  6:00 PM EAT daemon or instant CLI trigger    │
 └───────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │    Gmail SMTP (Port 465/587)  │
             │   Encrypted App Password Auth │
             └───────────────┬───────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │ Shop Owner Smartphone / Email │
             │  Executive HTML Report at 6pm │
             └───────────────────────────────┘
```

---

## 4. Realistic Sample Dataset

The included `sales_data.csv` represents a realistic day of trading at **Zawadi Mini-Mart & Provisions** along Ngong Road, Nairobi:

```csv
transaction_id,timestamp,item_name,category,quantity_sold,unit_price,payment_method,stock_remaining,restock_threshold
TXN-20261119-001,2026-11-19 08:15:20,Brookside Fresh Milk 500ml,Dairy,4,65.00,M-Pesa,18,12
TXN-20261119-002,2026-11-19 08:42:10,Broadways Sliced White Bread 400g,Bakery,6,65.00,Cash,3,10
TXN-20261119-003,2026-11-19 09:10:05,Pembe Maize Flour 2kg,Staples,3,215.00,M-Pesa,8,15
TXN-20261119-004,2026-11-19 09:55:40,Kabras Pure White Sugar 1kg,Staples,2,160.00,Cash,6,12
TXN-20261119-005,2026-11-19 10:30:15,Golden Fry Vegetable Cooking Oil 1L,Cooking Oils,1,320.00,M-Pesa,14,8
TXN-20261119-006,2026-11-19 11:12:50,Menengai Cream Bar Soap 1kg,Household,2,240.00,Cash,22,10
TXN-20261119-007,2026-11-19 11:45:00,Royco Mchuzi Mix Beef 200g,Seasoning,3,140.00,M-Pesa,16,8
TXN-20261119-008,2026-11-19 12:20:30,Ketepa Pride Tea Leaves 250g,Beverages,1,135.00,Cash,11,10
TXN-20261119-009,2026-11-19 13:05:15,Daima Strawberry Yoghurt 250ml,Dairy,5,95.00,M-Pesa,2,8
TXN-20261119-010,2026-11-19 13:40:22,Indomie Instant Noodles Chicken 120g,Quick Meals,8,50.00,Cash,45,20
TXN-20261119-011,2026-11-19 14:15:10,Geisha Bathing Soap 225g,Personal Care,2,110.00,Cash,19,10
TXN-20261119-012,2026-11-19 15:02:45,Tuzo Long Life Milk 500ml,Dairy,4,70.00,M-Pesa,25,10
TXN-20261119-013,2026-11-19 15:35:10,Brookside Fresh Milk 500ml,Dairy,5,65.00,M-Pesa,13,12
TXN-20261119-014,2026-11-19 16:10:00,Pembe Maize Flour 2kg,Staples,4,215.00,M-Pesa,4,15
TXN-20261119-015,2026-11-19 16:50:35,Mumias White Sugar 2kg,Staples,2,310.00,Cash,15,8
TXN-20261119-016,2026-11-19 17:35:12,Omo Hand Washing Powder 500g,Household,2,220.00,M-Pesa,5,10
```

### Flexible Data Schema Compatibility
The parser accommodates diverse real-world POS exports:
- Supports alternate header names: `item` / `product_name`, `qty` / `quantity_sold`, `price` / `unit_price`, `stock` / `current_stock`.
- Dual stock resolution: Reads remaining stock directly from the sales file OR looks up reference stock points in `inventory_reference.csv`.

---

## 5. Security & Credentials Management

This project strictly follows the 12-Factor App methodology for credentials management.

### Google App Password Configuration
Never use your standard Google password. To generate an authorized 16-character App Password:
1. Navigate to your **[Google Account Security Settings](https://myaccount.google.com/security)**.
2. Enable **2-Step Verification**.
3. Under **How you sign in to Google**, select **2-Step Verification** &gt; **App passwords** (or visit `https://myaccount.google.com/apppasswords`).
4. Enter an App Name (e.g. `Nairobi Retail Reporter`) and click **Create**.
5. Copy the generated 16-character password into your local `.env` file.

### Environment File (`.env`)
Create a local `.env` file (copied from `.env.example`):
```ini
GMAIL_ADDRESS=your_shop_account@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
REPORT_RECIPIENT=shop_owner@example.com
SHOP_NAME=Zawadi Mini-Mart & Provisions
SHOP_LOCATION=Westlands, Nairobi, Kenya
REPORT_TIME_EAT=18:00
DEFAULT_RESTOCK_THRESHOLD=10
```

### Git Exclusion Verification (`.gitignore`)
The `.env` file contains sensitive credentials and is strictly excluded via `.gitignore`:
```
.env
.env.*
!.env.example
__pycache__/
*.pyc
*.log
last_report.html
```

---

## 6. Installation & Execution

### Step 1: Clone Repository & Navigate to Directory
```bash
git clone https://github.com/branhamsimiyu8289/AI-Masterclass-II.git
cd "AI-Masterclass-II/Week5/day-23/retail-sales-reporter"
```

### Step 2: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the Script (Immediate Mode)
To calculate metrics, generate the HTML report, and dispatch the email immediately:
```bash
python sales_reporter.py --now
```

### Step 4: Run in Dry-Run / Preview Mode (No Email Sent)
To compute metrics and write an HTML preview to `last_report.html` without connecting to SMTP:
```bash
python sales_reporter.py --dry-run --preview last_report.html
```

### Step 5: Run in Continuous Daily Schedule Mode (6:00 PM EAT)
To keep the script running as a background service that triggers every evening at 18:00 (6:00 PM):
```bash
python sales_reporter.py --schedule --time 18:00
```

### Step 6: Run Automated Unit Tests
```bash
python -m unittest test_sales_reporter.py
```
*(Runs 8 automated unit tests covering revenue computation, transaction counts, top seller identification, restock flags, and HTML templating).*

---

## 7. Verified Email Delivery Evidence

During testing, the script was executed and successfully delivered the daily summary report via Google SMTP SSL.

### Console Execution Output
```text
=================================================================
 Zawadi Mini-Mart & Provisions - DAILY SALES SUMMARY
=================================================================
1. Total Revenue:         KES 6,590.00
2. Total Transactions:    16 orders
3. Top-Selling Item:      Brookside Fresh Milk 500ml (9 units, KES 585.00)
4. Restock Level Flag:    ⚠️ ALERT: Low stock detected!

   Low Stock Items:
     - Pembe Maize Flour 2kg: 4 left (min 15, need +11) [CRITICAL]
     - Broadways Sliced White Bread 400g: 3 left (min 10, need +7) [CRITICAL]
     - Kabras Pure White Sugar 1kg: 6 left (min 12, need +6) [CRITICAL]
     - Daima Strawberry Yoghurt 250ml: 2 left (min 8, need +6) [CRITICAL]
     - Omo Hand Washing Powder 500g: 5 left (min 10, need +5) [CRITICAL]
=================================================================
[INFO] Email successfully sent via SMTP_SSL (port 465) to branhamsimiyu8289@gmail.com
[INFO] Report dispatched successfully to: branhamsimiyu8289@gmail.com
```

### Inbox Verification (via IMAP RFC 822)
- **Subject**: `📊 Daily Sales Summary - Zawadi Mini-Mart & Provisions (2026-11-19) - KES 6,590.00 [⚠️ RESTOCK NEEDED]`
- **Status**: Received in Inbox with all 4 metrics clearly rendered.

---

## 8. Commercial Strategy: Pricing & Engagement Model

> **Requirement**: *What would you charge to build this for a shop owner, and whether you would charge a one-off fee or a monthly retainer?*

Building software for small and medium retail businesses in Kenya requires aligning technical value with tangible cash flow improvements (preventing stockouts, stopping cashier pilferage, and saving owners 45 minutes of manual tallying each evening).

### A. Recommended Pricing Structure

| Model | Pricing (KES) | Pricing (USD) | Scope & Deliverables | Best Suited For |
|---|---|---|---|---|
| **Option 1: One-Off Implementation Fee** | **KES 35,000 – 45,000** | ~$270 – $350 USD | • Custom CSV schema mapping to shop's POS/Excel<br>• HTML email styling with shop logo & branding<br>• Local Windows Task Scheduler setup on cashier PC<br>• Gmail 2FA & App Password configuration<br>• Cashier standard operating procedure (SOP) guide<br>• 14 days post-launch warranty & bug fixes | Tech-savvy owners with an existing stable POS who only need the automation built and handed over. |
| **Option 2: Monthly Managed Retainer** | **KES 5,000 – 7,500 / month** *(+ KES 15,000 onboarding)* | ~$40 – $60 / month *(+ $115 onboarding)* | • Dedicated cloud hosting (lightweight cloud instance)<br>• Daily delivery monitoring & failure alerting<br>• Handling cashier staff turnover & retraining<br>• Fixing CSV format corruptions (e.g. cashier typo in column)<br>• Monthly sales trend analysis & quarterly threshold reviews<br>• Priority WhatsApp support SLA (under 2 hours) | Busy owners managing 1 to 3 shops who want guaranteed reporting without IT headaches. |
| **Option 3: Hybrid Retainer Model (RECOMMENDED)** | **KES 25,000 Setup + KES 3,500 / month** | ~$190 Setup + $27 / month | • Complete installation, styling, and local/cloud setup<br>• Low upfront barrier to close the sale<br>• Continuous delivery guarantee, log rotation, and maintenance<br>• Quarterly feature updates (e.g. M-Pesa fee deduction) | **The sweet spot for Nairobi retailers.** Low upfront commitment with steady recurring revenue. |

---

### B. One-Off vs. Monthly Retainer: Strategic Justification

#### Why a Pure One-Off Model Fails in Practice:
1. **Cashier Turnover**: In Nairobi retail dukas, cashier turnover is high. A new cashier inevitably renames columns (e.g. changes `quantity_sold` to `Qty`), breaking a rigid script. A pure one-off project leaves the client dissatisfied when it breaks 6 weeks later.
2. **Google App Password Rotations**: Google security changes or password resets periodically invalidate App Passwords. Without ongoing support, the owner stops receiving reports and assumes the software is broken.
3. **No Recurring Revenue**: The consultant expends sales effort once for KES 35,000 and misses long-term client lifetime value (LTV).

#### Why the Retainer Model Wins for Both Sides:
- **For the Shop Owner**: For less than the daily profit of selling two bags of sugar (`~KES 115/day`), the owner gets complete peace of mind. If the cashier forgets to update the CSV, the system alerts the owner. If stock runs out, the owner knows at 6:00 PM and places orders with wholesalers (e.g. Twiga Foods or Eastleigh distributors) for delivery early the next morning.
- **For the Developer**: A portfolio of 10 retail clients on a KES 4,500/month retainer generates **KES 45,000/month in passive recurring revenue** for approximately 2 to 3 hours of maintenance per month.

---

### C. Future High-Value Upsell Roadmap

Once the basic daily sales email is established, you can upsell advanced automation modules:
1. **M-Pesa Daraja API Direct Reconciliation (+KES 30,000 setup)**:
   Connect Safaricom's Daraja C2B/B2C API to automatically cross-verify cash received in the till against actual M-Pesa Paybill/Till transactions, eliminating cashier skimming.
2. **WhatsApp Business Notification Bot (+KES 2,000/month)**:
   Deliver the 4 metrics as a 6:00 PM instant WhatsApp message via Twilio or Meta WhatsApp Cloud API for owners who check WhatsApp more frequently than email.
3. **Multi-Branch Consolidated Dashboard (+KES 5,000/month)**:
   Aggregate reports from 3+ branches (e.g. Westlands, Rongai, Eastleigh) into a single consolidated comparison email.

---

## 9. Repository Structure

```
retail-sales-reporter/
├── .env.example              # Template environment configuration
├── .gitignore                # Protects .env, logs, and build artifacts
├── inventory_reference.csv   # Catalog reference with stock thresholds & pack sizes
├── sales_data.csv            # 16-row realistic Nairobi sales transaction log
├── sales_reporter.py         # Main pipeline (parsers, metrics, emailer, scheduler)
├── test_sales_reporter.py    # Automated test suite (8 test cases)
├── requirements.txt          # Python dependencies (python-dotenv, schedule)
└── README.md                 # Complete technical documentation & pricing strategy
```

---

## 10. License & Credits

Developed as part of the **AI-Masterclass II Engineering Curriculum** &bull; Week 5 (Email & Data Pipeline Automation).
Available under the MIT License.
