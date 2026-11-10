# Kiambu Poultry Farm - Egg Production Manager & API

A real-world production logging system built with FastAPI to solve daily egg record-keeping and weekly reconciliation for a poultry farmer with three sheds in Kiambu, Kenya.

---

## 🌾 The Real Problem Being Solved

In Kiambu, layer poultry farmers routinely collect eggs from multiple sheds every evening. Historically, the farmer typed raw daily numbers into a personal WhatsApp chat:

```text
Monday: Shed 1 - 412, Shed 2 - 388, Shed 3 - 295
Tuesday: Shed 1 - 405, Shed 2 - 391, Shed 3 - 302
...
```

On Saturday afternoon, the farmer had to:
1. Manually scroll through the chat messages.
2. Pull out a calculator to sum each shed's yields.
3. Convert loose egg counts into **commercial trays** (in Kenya, eggs are packed and sold in 30-egg trays: `trays = count // 30`).
4. Spot errors or typos with no way to edit past logs.

This application solves that exact problem:
- **Zero Data Loss**: Persistent SQLite database (`eggs.db`) ensures records survive server restarts.
- **Farmer Dashboard (`/`)**: A clean, mobile-first web app accessible directly on a phone or laptop in the sheds.
- **Commercial Tray Calculations**: Real-time conversion of loose egg counts into full 30-egg crates/trays + remaining loose eggs.
- **Saturday WhatsApp Reconciler**: Generates a pre-formatted, professional weekly report that can be copied or opened directly in WhatsApp with a single click.
- **Masterclass REST API**: 100% compliant with the classroom exercise endpoints (`POST /api/eggs`, `GET /api/eggs`) with running totals and date filtering.

---

## 🚀 Getting Started

### 1. Activate Environment and Install Dependencies

From this folder:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Start the Application

```powershell
python -m uvicorn main:app --reload
```

- **Interactive Farmer Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📱 Features

1. **Daily Quick Log**:
   - Quick shed selector buttons (`Shed 1`, `Shed 2`, `Shed 3`).
   - Quick tray modifiers (`+30 (1 Tray)`, `+10`, `-10`).
   - Input validation (rejects negative counts, blank shed names, invalid dates).

2. **Saturday WhatsApp Reconciler**:
   - Aggregates the last 7 days of production.
   - Calculates total full trays (30s) and loose eggs per shed.
   - Prepares formatted WhatsApp text:
     ```text
     🐔 *KIAMBU POULTRY FARM - WEEKLY RECONCILIATION*
     📅 *Week:* Mon 03 Nov – Sun 09 Nov 2026
     ━━━━━━━━━━━━━━━━━━━━━━
     🏠 *Shed 1:* 2,876 eggs (95 trays + 26 loose)
     🏠 *Shed 2:* 2,739 eggs (91 trays + 9 loose)
     🏠 *Shed 3:* 2,112 eggs (70 trays + 12 loose)
     ━━━━━━━━━━━━━━━━━━━━━━
     🥚 *Grand Total:* 7,727 eggs
     📦 *Commercial Trays:* 257 full trays (17 loose)
     ━━━━━━━━━━━━━━━━━━━━━━
     Logged via Kiambu Farm API 🚀
     ```

3. **Persistent SQLite Database**:
   - Data is stored in `eggs.db` in this folder.
   - Survives server restarts.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Responsive Farmer Web Dashboard |
| `POST` | `/api/eggs` | Log a daily record (`shed`, `date`, `count`) |
| `GET` | `/api/eggs` | Get all records with running total and totals by shed (supports `start` and `end` query params) |
| `GET` | `/api/eggs/weekly-summary` | 7-day aggregation with 30-egg tray math & WhatsApp message |
| `DELETE` | `/api/eggs/{id}` | Delete a record by ID |
| `POST` | `/api/eggs/seed-sample` | Pre-load 1-week Kiambu farm sample data across 3 sheds |
| `DELETE` | `/api/eggs` | Reset all records |

### Example cURL Requests

**Log daily production (POST):**
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/eggs `
  -H "Content-Type: application/json" `
  -d '{"shed":"Shed 1","date":"2026-11-09","count":412}'
```

**Get all logs with running total (GET):**
```powershell
curl.exe http://127.0.0.1:8000/api/eggs
```

**Filter logs by date range:**
```powershell
curl.exe "http://127.0.0.1:8000/api/eggs?start=2026-11-03&end=2026-11-05"
```

**Get Saturday weekly reconciliation:**
```powershell
curl.exe http://127.0.0.1:8000/api/eggs/weekly-summary
```

---

## 🧪 Running the Unit Tests

Run the test suite with:

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest -v test_api
```

All tests run in isolated async mode, testing both the core classroom requirements and the extended real-world features.
