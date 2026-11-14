[LIVE DEMO](https://egg-production-tracker-v8w1.onrender.com/)

# Kiambu Poultry Farm - Egg Production Tracker (Full-Stack)

A lightweight, full-stack web application built for poultry farmers and farm managers in Kenya (such as Kiambu's egg-producing peri-urban belt). It replaces ad-hoc WhatsApp self-messages and manual Saturday calculations with an interactive browser dashboard powered by a Flask REST API.

---

## 🚀 Key Features

1. **Interactive Web Interface**:
   - Clean, mobile-friendly dashboard accessible on smartphones, tablets, or desktop browsers.
   - Direct form entry for **Shed Name**, **Date**, and **Egg Count**.
   - Preset buttons for fast selection (`Shed 1`, `Shed 2`, `Shed 3`).
   - Dynamic commercial tray calculator (converts total count to trays of 30 eggs + loose eggs).

2. **Real-Time Client-Side Updates (No Page Reload)**:
   - Uses JavaScript `fetch()` to dispatch `POST /api/eggs` without refreshing the page.
   - Automatically triggers `GET /api/eggs` following successful submission.
   - Renders a live table below the form displaying every logged entry with its ongoing **Running Total**.
   - Immediately updates the cumulative egg count and active shed summary banners.

3. **REST API**:
   - `POST /api/eggs`: Validates input and stores records in SQLite.
   - `GET /api/eggs`: Computes cumulative running totals across entries, calculates per-shed breakdowns, and returns structured JSON.
   - `DELETE /api/eggs`: Disabled unless `RESET_TOKEN` is configured; then requires that token as a bearer token.

---

## 📂 Project Structure

```text
C:\Users\owen chole\Desktop\AI-Masterclass II\AI-Masterclass-II\Week4\day-18\full-stack\
├── app.py                  # Flask REST API backend & static route handler
├── templates/
│   └── index.html          # Interactive browser interface with HTML, CSS & JavaScript fetch()
├── test_app.py             # Integration test suite (validates POSTs, GETs & UI)
├── requirements.txt        # Python package dependencies
└── README.md               # Documentation & Kenyan SME Market/Pricing Analysis
```

---

## 🛠️ Getting Started

### 1. Requirements
- Python 3.10+
- Flask (`pip install -r requirements.txt`)

### 2. Installation
Open VS Code in this directory:
```bash
cd "C:\Users\owen chole\Desktop\AI-Masterclass II\AI-Masterclass-II\Week4\day-18\full-stack"
python -m pip install -r requirements.txt
```

Use the same Python interpreter for installing dependencies and running the
app. In VS Code, select that interpreter if Flask cannot be imported.

### 3. Run the Application
```bash
python app.py
```
Open your web browser and navigate to:
**`http://127.0.0.1:5000`**

### 4. Run Automated Tests
```bash
python test_app.py
```

## Deploy to Render

The `AI-Masterclass-II` repository includes a `render.yaml` Blueprint. Connect
that repository in Render and create a Blueprint. It sets the app directory,
installs `requirements.txt`, runs Gunicorn, and mounts a persistent disk at
`/var/data` for the SQLite database. The persistent disk requires a paid Render
web-service plan.

The app's reset endpoint is disabled by default. To enable it, add a strong
`RESET_TOKEN` environment variable in Render and send it as
`Authorization: Bearer <token>` when calling `DELETE /api/eggs`. Keep the token
private.

The service health check is available at `/healthz`.

---

## 🧪 Testing the Live Interface

1. Open `http://127.0.0.1:5000` in your browser.
2. Select **Shed 1**, choose today's date, input `140` eggs, and click **Submit Record**.
   - Notice the toast confirmation and that the page **does not reload**.
   - The **Total Eggs Logged** card instantly jumps to **140**.
   - The table row displays `#1 | Shed 1 | 140 eggs | Running Total: 140`.
3. Select **Shed 2**, input `165` eggs, and click **Submit Record**.
   - Total eggs updates to **305**.
   - The table appends `#2 | Shed 2 | 165 eggs | Running Total: 305`.
4. Submit two more entries across Shed 1 and Shed 2 to verify cumulative continuity.

---

## 🇰🇪 Kenyan Market Analysis: Target Small Businesses & Pricing Strategy

A simple, reliable daily logging tool with cumulative running totals and zero page-reload overhead solves a massive pain point across Kenya's informal and semi-formal small and medium enterprises (SMEs).

### 1. Target Small Business Categories in Kenya

| Business Category | Local Context / Regions | Daily Workflow Pain Point Solved |
| :--- | :--- | :--- |
| **Poultry & Egg Farmers** | Kiambu (Ruaka, Kikuyu, Wangige), Machakos, Nakuru, Naivasha | Farmers currently jot daily collections on paper or WhatsApp chats. At weekend collection by egg brokers, totals are disputed and trays (30 eggs/tray) miscounted. |
| **Dairy Milk Collection Hubs** | Nyandarua, Meru, Eldoret, Nyeri, Limuru | Small private cooperatives or collection centers record morning and evening liters per farmer. Wet ledgers get torn or damaged; a lightweight mobile web log prevents lost records. |
| **Posho Mills & Grain Millers** | Western Kenya, Eldoret, Nairobi peri-urban (Kawangware, Pipeline) | Milling operators track raw maize bags in versus packed flour kilograms out per milling machine to detect pilferage and grain loss. |
| **Water Refill Kiosks & Water ATMs** | Kasarani, Roysambu, Rongai, Embakasi | Dispensing attendants record 10L/20L bottle refills per nozzle. A running total cross-references water meter units with cash/M-Pesa till receipts. |
| **Wholesale Egg Depots & Distributors** | Eastleigh, Wakulima Market, Muthurwa, City Market | Middlemen receive egg crates from Kiambu farms and redistribute them to local retail kiosks (*vibandas*). Running totals track intact stock versus breakage loss. |
| **Neighborhood Bakeries & Butchery Kiosks** | Commercial urban centers nationwide | Bakers track bread batch yields per oven shift; butchers record daily carcass cold-weight versus cuts sold. |

---

### 2. Proposed Pricing Model & Price Points (in KES)

Kenyan micro-businesses are price-sensitive but willing to pay for software that **directly protects revenue**, **prevents staff theft**, and **integrates with M-Pesa**.

#### **Tier 1: Lite / Micro-Farmer Tier (Freemium or KES 300 – KES 500 / month)**
* **Target Audience**: Single smallholder farmers (1–2 sheds, <1,000 birds) or standalone water kiosks.
* **Included Features**:
  - Daily logging for up to 3 sheds/units.
  - In-browser running totals and table view.
  - Weekly summary generator.
* **Billing**: M-Pesa monthly prompt (Lipa Na M-Pesa Till / STK push).

#### **Tier 2: Pro SME Plan (KES 1,200 – KES 2,500 / month)**
* **Target Audience**: Commercial poultry farms (3–10 sheds), wholesale distributors, independent milk hubs.
* **Included Features**:
  - Unlimited sheds, units, and collection points.
  - Multi-user access (Shed Workers can only log; Farm Manager can view and edit).
  - 1-click **WhatsApp Saturday Reconciliation** message generation to share with buyers/cooperatives.
  - CSV/Excel download for accounting and bookkeeping.
  - SMS end-of-day summary trigger to owner's phone.

#### **Tier 3: Cooperative / Custom Setup (KES 15,000 – KES 35,000 one-off or KES 5,000/month)**
* **Target Audience**: Saccos, farmer groups, milk cooperatives, and regional distribution depots.
* **Included Features**:
  - Multi-farmer supplier accounts (50+ suppliers/farmers).
  - Automated SMS receipts sent to each farmer upon daily delivery confirmation.
  - M-Pesa Daraja B2C integration for automated weekly supplier payouts.
  - Dedicated offline-first local deployment with cloud backup.

---

### 3. Key Adoption Drivers for Kenya
1. **Low Data Overhead**: Fast, lightweight single-page interface that consumes minimal mobile data bundles.
2. **Offline-Friendly Caching**: Service-worker or local storage backup when cellular reception in agricultural areas fluctuates.
3. **M-Pesa Integration**: Frictionless subscription renewals via M-Pesa STK Push rather than credit cards.
