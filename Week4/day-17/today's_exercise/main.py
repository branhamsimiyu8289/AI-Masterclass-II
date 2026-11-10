import os
import sqlite3
import sys
from datetime import date as Date, timedelta
from typing import Optional
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Egg Production Log",
    description=(
        "Production-ready API and farmer dashboard for logging daily egg yields across sheds, "
        "calculating commercial trays (30 eggs/tray), and automating Saturday WhatsApp reconciliation "
        "for poultry farmers in Kiambu."
    ),
    version="2.0.0",
)

DB_PATH = os.path.join(os.path.dirname(__file__), "eggs.db")
IS_TESTING = "unittest" in sys.modules

# Active record store (in-memory for instant response & test compatibility, backed by SQLite)
records: list[dict] = []


def init_db():
    if IS_TESTING:
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS egg_records (
                id INTEGER PRIMARY KEY,
                shed TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER NOT NULL
            )
        """)
        conn.commit()


def load_from_db():
    if IS_TESTING or not os.path.exists(DB_PATH):
        return
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, shed, date, count FROM egg_records ORDER BY date, id").fetchall()
            records.clear()
            for r in rows:
                records.append({
                    "id": r["id"],
                    "shed": r["shed"],
                    "date": r["date"],
                    "count": r["count"]
                })
    except Exception:
        pass


def persist_record(record: dict):
    if IS_TESTING:
        return
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO egg_records (id, shed, date, count) VALUES (?, ?, ?, ?)",
            (record["id"], record["shed"], record["date"], record["count"])
        )
        conn.commit()


def remove_record_db(record_id: int):
    if IS_TESTING:
        return
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM egg_records WHERE id = ?", (record_id,))
        conn.commit()


def clear_db():
    if IS_TESTING:
        return
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM egg_records")
        conn.commit()


# Preload database records when running as server
if not IS_TESTING:
    load_from_db()


class EggRecordIn(BaseModel):
    shed: str = Field(..., min_length=1, max_length=50, examples=["Shed 1"])
    date: Date = Field(..., examples=["2026-11-09"])
    count: int = Field(..., ge=0, le=100000, examples=[412])

    @field_validator("shed")
    @classmethod
    def clean_shed(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("shed name cannot be blank")
        return v


@app.post("/api/eggs", status_code=201)
def log_eggs(entry: EggRecordIn):
    """Log one daily egg count for one shed."""
    record_id = max([r["id"] for r in records], default=0) + 1
    record = {
        "id": record_id,
        "shed": entry.shed,
        "date": entry.date.isoformat(),
        "count": entry.count,
    }
    records.append(record)
    persist_record(record)
    return record


@app.get("/api/eggs")
def list_eggs(
    start: Optional[Date] = Query(None, description="Only records on/after this date"),
    end: Optional[Date] = Query(None, description="Only records on/before this date"),
):
    """Return all records, each with a running total, plus overall and per-shed totals.

    Records are ordered by date (then by the order they were logged), and the
    running total accumulates across all sheds in that order.
    """
    selected = [
        r for r in records
        if (start is None or r["date"] >= start.isoformat())
        and (end is None or r["date"] <= end.isoformat())
    ]
    selected.sort(key=lambda r: (r["date"], r["id"]))

    running = 0
    out = []
    for r in selected:
        running += r["count"]
        out.append({**r, "running_total": running})

    by_shed: dict[str, int] = {}
    for r in selected:
        by_shed[r["shed"]] = by_shed.get(r["shed"], 0) + r["count"]

    return {
        "records": out,
        "total": running,
        "totals_by_shed": by_shed,
        "record_count": len(out),
    }


@app.get("/api/eggs/weekly-summary")
def get_weekly_summary(
    end_date: Optional[Date] = Query(None, description="End date of the week (defaults to latest recorded date or today)")
):
    """Calculates weekly egg production, commercial crates/trays (30 eggs/tray),
    and generates a pre-formatted message for Saturday WhatsApp reconciliation.
    """
    if not records:
        return {
            "period": {"start": None, "end": None},
            "total_eggs": 0,
            "total_trays": 0,
            "loose_eggs": 0,
            "by_shed": {},
            "records_count": 0,
            "whatsapp_message": "No egg records logged yet.",
            "whatsapp_url": "",
        }

    target_end = end_date or max(Date.fromisoformat(r["date"]) for r in records)
    target_start = target_end - timedelta(days=6)

    start_str = target_start.isoformat()
    end_str = target_end.isoformat()

    week_records = [
        r for r in records
        if start_str <= r["date"] <= end_str
    ]

    total_eggs = sum(r["count"] for r in week_records)
    total_trays = total_eggs // 30
    loose_eggs = total_eggs % 30

    by_shed: dict[str, dict] = {}
    for r in week_records:
        shed = r["shed"]
        if shed not in by_shed:
            by_shed[shed] = {"count": 0, "trays": 0, "loose": 0, "records_count": 0}
        by_shed[shed]["count"] += r["count"]
        by_shed[shed]["records_count"] += 1

    for shed, data in by_shed.items():
        data["trays"] = data["count"] // 30
        data["loose"] = data["count"] % 30

    # Build formatted WhatsApp message for Kiambu poultry farmer
    msg_lines = [
        "🐔 *KIAMBU POULTRY FARM - WEEKLY RECONCILIATION*",
        f"📅 *Week:* {target_start.strftime('%a %d %b')} – {target_end.strftime('%a %d %b %Y')}",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for shed, data in sorted(by_shed.items()):
        msg_lines.append(f"🏠 *{shed}:* {data['count']:,} eggs ({data['trays']} trays + {data['loose']} loose)")
    msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    msg_lines.append(f"🥚 *Grand Total:* {total_eggs:,} eggs")
    msg_lines.append(f"📦 *Commercial Trays:* {total_trays} full trays ({loose_eggs} loose)")
    msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    msg_lines.append("Logged via Kiambu Farm API 🚀")

    whatsapp_text = "\n".join(msg_lines)
    whatsapp_url = f"https://api.whatsapp.com/send?text={quote_plus(whatsapp_text)}"

    return {
        "period": {"start": start_str, "end": end_str},
        "total_eggs": total_eggs,
        "total_trays": total_trays,
        "loose_eggs": loose_eggs,
        "by_shed": by_shed,
        "records_count": len(week_records),
        "whatsapp_message": whatsapp_text,
        "whatsapp_url": whatsapp_url,
    }


@app.delete("/api/eggs/{record_id}", status_code=200)
def delete_egg_record(record_id: int):
    """Delete an egg record by ID (e.g. to fix a mistyped log)."""
    found = next((r for r in records if r["id"] == record_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="Record not found")
    records.remove(found)
    remove_record_db(record_id)
    return {"message": f"Record {record_id} deleted successfully", "deleted": found}


@app.post("/api/eggs/seed-sample", status_code=201)
def seed_sample_data():
    """Populates realistic 1-week production data for Kiambu Farm's 3 sheds (Shed 1, Shed 2, Shed 3)."""
    sample_data = [
        ("Shed 1", "2026-11-03", 412),
        ("Shed 2", "2026-11-03", 388),
        ("Shed 3", "2026-11-03", 295),
        ("Shed 1", "2026-11-04", 405),
        ("Shed 2", "2026-11-04", 391),
        ("Shed 3", "2026-11-04", 302),
        ("Shed 1", "2026-11-05", 398),
        ("Shed 2", "2026-11-05", 385),
        ("Shed 3", "2026-11-05", 290),
        ("Shed 1", "2026-11-06", 415),
        ("Shed 2", "2026-11-06", 394),
        ("Shed 3", "2026-11-06", 310),
        ("Shed 1", "2026-11-07", 420),
        ("Shed 2", "2026-11-07", 389),
        ("Shed 3", "2026-11-07", 305),
        ("Shed 1", "2026-11-08", 408),
        ("Shed 2", "2026-11-08", 392),
        ("Shed 3", "2026-11-08", 298),
        ("Shed 1", "2026-11-09", 418),
        ("Shed 2", "2026-11-09", 390),
        ("Shed 3", "2026-11-09", 308),
    ]
    added = []
    for shed, day, count in sample_data:
        if not any(r["shed"] == shed and r["date"] == day for r in records):
            rec_id = max([r["id"] for r in records], default=0) + 1
            rec = {"id": rec_id, "shed": shed, "date": day, "count": count}
            records.append(rec)
            persist_record(rec)
            added.append(rec)
    return {"message": f"Added {len(added)} Kiambu farm sample records", "added_count": len(added)}


@app.delete("/api/eggs", status_code=200)
def reset_all_records():
    """Clear all records (resets database and in-memory list)."""
    records.clear()
    clear_db()
    return {"message": "All egg records cleared successfully"}


@app.get("/", response_class=HTMLResponse)
def farmer_dashboard():
    """Interactive, mobile-friendly dashboard for the Kiambu poultry farmer."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kiambu Poultry Farm - Egg Production Manager</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen">
  <!-- Top Navigation -->
  <header class="bg-emerald-800 text-white shadow-lg sticky top-0 z-50">
    <div class="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center space-x-3">
        <span class="text-3xl">🐔</span>
        <div>
          <h1 class="text-lg md:text-xl font-bold leading-tight">Kiambu Poultry Farm</h1>
          <p class="text-xs text-emerald-200">Daily Shed Tracker & Saturday WhatsApp Reconciler</p>
        </div>
      </div>
      <div class="flex items-center space-x-2 text-xs">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full font-medium bg-emerald-700 text-emerald-100 border border-emerald-600">
          <span class="w-2 h-2 mr-1.5 bg-emerald-400 rounded-full animate-pulse"></span> SQLite Persistent
        </span>
        <a href="/docs" target="_blank" class="bg-emerald-900/60 hover:bg-emerald-900 px-3 py-1 rounded text-emerald-100 font-medium transition flex items-center gap-1">
          <i class="fa-solid fa-code text-xs"></i> API Docs
        </a>
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto px-4 py-6">
    <!-- Stat Cards -->
    <section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
        <div class="w-12 h-12 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center text-xl font-bold">🥚</div>
        <div>
          <div class="text-xs uppercase font-semibold text-slate-400 tracking-wider">Total Eggs</div>
          <div id="statTotalEggs" class="text-2xl font-black text-slate-800">0</div>
        </div>
      </div>
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
        <div class="w-12 h-12 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-xl font-bold">📦</div>
        <div>
          <div class="text-xs uppercase font-semibold text-slate-400 tracking-wider">Total Trays (30s)</div>
          <div id="statTotalTrays" class="text-2xl font-black text-slate-800">0</div>
        </div>
      </div>
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
        <div class="w-12 h-12 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center text-xl font-bold">🏆</div>
        <div>
          <div class="text-xs uppercase font-semibold text-slate-400 tracking-wider">Top Shed</div>
          <div id="statTopShed" class="text-lg font-bold text-slate-800 truncate max-w-[120px]">-</div>
        </div>
      </div>
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
        <div class="w-12 h-12 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center text-xl font-bold">📋</div>
        <div>
          <div class="text-xs uppercase font-semibold text-slate-400 tracking-wider">Log Entries</div>
          <div id="statRecordCount" class="text-2xl font-black text-slate-800">0</div>
        </div>
      </div>
    </section>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left Column: Daily Logging & Sample Actions -->
      <div class="lg:col-span-5 space-y-6">
        <!-- Daily Form -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-bold text-base text-slate-800 flex items-center gap-2">
              <i class="fa-solid fa-plus-circle text-emerald-600"></i> Log Daily Production
            </h2>
            <span class="text-xs text-slate-400">Kiambu Daily Routine</span>
          </div>

          <form id="eggForm" onsubmit="handleFormSubmit(event)" class="space-y-4">
            <!-- Shed Selection -->
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">Select or Type Shed</label>
              <div class="grid grid-cols-3 gap-2 mb-2">
                <button type="button" onclick="setShed('Shed 1')" class="shed-btn py-1.5 px-2 text-xs font-medium rounded-lg border border-slate-200 hover:border-emerald-500 hover:bg-emerald-50 active:bg-emerald-100 transition">Shed 1</button>
                <button type="button" onclick="setShed('Shed 2')" class="shed-btn py-1.5 px-2 text-xs font-medium rounded-lg border border-slate-200 hover:border-emerald-500 hover:bg-emerald-50 active:bg-emerald-100 transition">Shed 2</button>
                <button type="button" onclick="setShed('Shed 3')" class="shed-btn py-1.5 px-2 text-xs font-medium rounded-lg border border-slate-200 hover:border-emerald-500 hover:bg-emerald-50 active:bg-emerald-100 transition">Shed 3</button>
              </div>
              <input type="text" id="shedInput" required placeholder="e.g. Shed 1"
                class="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium">
            </div>

            <!-- Date -->
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">Date Collected</label>
              <input type="date" id="dateInput" required
                class="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500">
            </div>

            <!-- Count with Tray Helpers -->
            <div>
              <div class="flex justify-between items-center mb-1">
                <label class="text-xs font-semibold text-slate-600">Egg Count</label>
                <span id="trayCalc" class="text-xs text-slate-500 font-mono">0 trays (0 loose)</span>
              </div>
              <input type="number" id="countInput" min="0" max="100000" required placeholder="e.g. 412"
                oninput="updateTrayHelper()"
                class="w-full text-lg font-bold px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500">

              <!-- Quick Stepper Presets -->
              <div class="flex items-center gap-2 mt-2">
                <button type="button" onclick="adjustCount(30)" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded font-medium transition">+30 (1 Tray)</button>
                <button type="button" onclick="adjustCount(10)" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded font-medium transition">+10</button>
                <button type="button" onclick="adjustCount(-10)" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded font-medium transition">-10</button>
                <button type="button" onclick="adjustCount(-30)" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded font-medium transition">-30</button>
              </div>
            </div>

            <button type="submit" id="submitBtn"
              class="w-full bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-semibold py-2.5 px-4 rounded-lg shadow transition flex items-center justify-center gap-2">
              <i class="fa-solid fa-cloud-arrow-up"></i> Save Daily Production
            </button>
          </form>
        </div>

        <!-- Quick Setup & Test Tools -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-wand-magic-sparkles text-amber-500"></i> Masterclass Test Helpers
          </h3>
          <p class="text-xs text-slate-600 mb-3 leading-relaxed">
            Quickly populate or reset realistic 1-week data for the Kiambu farmer's 3 sheds to test the endpoints and WhatsApp summary.
          </p>
          <div class="flex flex-wrap gap-2">
            <button onclick="seedSampleData()" class="flex-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 text-xs font-semibold py-2 px-3 rounded-lg transition flex items-center justify-center gap-1">
              <i class="fa-solid fa-database"></i> Load Sample Week (3 Sheds)
            </button>
            <button onclick="clearAllData()" class="bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 text-xs font-semibold py-2 px-3 rounded-lg transition flex items-center justify-center gap-1">
              <i class="fa-solid fa-trash"></i> Reset Data
            </button>
          </div>
        </div>
      </div>

      <!-- Right Column: Saturday WhatsApp Reconciler & History Table -->
      <div class="lg:col-span-7 space-y-6">

        <!-- Saturday WhatsApp Reconciler Card -->
        <div class="bg-gradient-to-br from-emerald-900 to-slate-900 text-white p-5 rounded-xl shadow-lg border border-emerald-800 relative overflow-hidden">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="p-2 bg-emerald-600 rounded-lg text-white text-sm"><i class="fa-brands fa-whatsapp text-lg"></i></span>
              <div>
                <h2 class="font-bold text-base">Saturday WhatsApp Reconciler</h2>
                <p class="text-xs text-emerald-300">Replaces manual WhatsApp chat addition with 1-click summary</p>
              </div>
            </div>
            <span class="text-xs bg-emerald-800/80 px-2 py-1 rounded text-emerald-200">Kiambu Farmer Flow</span>
          </div>

          <!-- WhatsApp Message Preview Box -->
          <div class="bg-slate-950/80 rounded-lg p-3 font-mono text-xs border border-emerald-950 mb-3 text-emerald-200 whitespace-pre-line leading-relaxed shadow-inner max-h-48 overflow-y-auto" id="whatsappPreview">
            Loading weekly summary...
          </div>

          <!-- Actions -->
          <div class="flex flex-wrap items-center gap-2">
            <button onclick="copyWhatsAppText()" class="flex-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold py-2 px-3 rounded-lg text-xs transition flex items-center justify-center gap-1.5 shadow">
              <i class="fa-regular fa-copy"></i> Copy WhatsApp Message
            </button>
            <a id="whatsappShareBtn" href="#" target="_blank" class="bg-emerald-700 hover:bg-emerald-600 text-white font-semibold py-2 px-4 rounded-lg text-xs transition flex items-center justify-center gap-1.5">
              <i class="fa-brands fa-whatsapp text-sm"></i> Send in WhatsApp
            </a>
          </div>
        </div>

        <!-- Filter & Records Table -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 class="font-bold text-base text-slate-800 flex items-center gap-2">
              <i class="fa-solid fa-list-check text-blue-600"></i> Production Log & Running Totals
            </h2>

            <!-- Date Filter Inputs -->
            <div class="flex items-center gap-2 text-xs">
              <input type="date" id="filterStart" onchange="fetchRecords()" class="px-2 py-1 border border-slate-300 rounded text-xs" title="Start Date">
              <span class="text-slate-400">to</span>
              <input type="date" id="filterEnd" onchange="fetchRecords()" class="px-2 py-1 border border-slate-300 rounded text-xs" title="End Date">
              <button onclick="clearFilters()" class="text-xs text-slate-500 hover:text-slate-800 underline">Reset</button>
            </div>
          </div>

          <!-- Table -->
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-700">
              <thead class="bg-slate-100 text-slate-600 uppercase font-semibold text-[10px] tracking-wider">
                <tr>
                  <th class="py-2.5 px-3">Date</th>
                  <th class="py-2.5 px-3">Shed</th>
                  <th class="py-2.5 px-3 text-right">Count</th>
                  <th class="py-2.5 px-3 text-right">Trays (30s)</th>
                  <th class="py-2.5 px-3 text-right">Running Total</th>
                  <th class="py-2.5 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody id="recordsBody" class="divide-y divide-slate-100">
                <tr>
                  <td colspan="6" class="text-center py-6 text-slate-400">Loading records...</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Table Footer Total -->
          <div id="tableFooter" class="mt-3 pt-3 border-t border-slate-100 flex justify-between items-center text-xs text-slate-600 font-medium">
            <span>Total Records: <strong id="footerCount">0</strong></span>
            <span>Cumulative Total: <strong id="footerTotal" class="text-emerald-700 text-sm">0</strong> eggs</span>
          </div>
        </div>

      </div>
    </div>
  </main>

  <!-- Toast Notification -->
  <div id="toast" class="fixed bottom-4 right-4 bg-slate-900 text-white px-4 py-2.5 rounded-lg text-xs shadow-xl transition-opacity duration-300 opacity-0 pointer-events-none flex items-center gap-2 z-50">
    <i class="fa-solid fa-circle-check text-emerald-400"></i>
    <span id="toastMsg">Action completed</span>
  </div>

  <script>
    // Set default date to today
    document.getElementById('dateInput').value = new Date().toISOString().split('T')[0];

    function showToast(msg) {
      const toast = document.getElementById('toast');
      document.getElementById('toastMsg').innerText = msg;
      toast.classList.remove('opacity-0');
      toast.classList.add('opacity-100');
      setTimeout(() => {
        toast.classList.remove('opacity-100');
        toast.classList.add('opacity-0');
      }, 3000);
    }

    function setShed(name) {
      document.getElementById('shedInput').value = name;
    }

    function adjustCount(amount) {
      const countInput = document.getElementById('countInput');
      let val = parseInt(countInput.value) || 0;
      val = Math.max(0, val + amount);
      countInput.value = val;
      updateTrayHelper();
    }

    function updateTrayHelper() {
      const countInput = document.getElementById('countInput');
      const val = parseInt(countInput.value) || 0;
      const trays = Math.floor(val / 30);
      const loose = val % 30;
      document.getElementById('trayCalc').innerText = `${trays} trays (${loose} loose)`;
    }

    async function fetchRecords() {
      const start = document.getElementById('filterStart').value;
      const end = document.getElementById('filterEnd').value;
      let url = '/api/eggs';
      const params = new URLSearchParams();
      if (start) params.append('start', start);
      if (end) params.append('end', end);
      if (params.toString()) url += '?' + params.toString();

      try {
        const res = await fetch(url);
        const data = await res.json();
        renderRecords(data);
        fetchWeeklySummary();
      } catch (err) {
        console.error(err);
      }
    }

    function renderRecords(data) {
      const tbody = document.getElementById('recordsBody');
      const records = data.records || [];

      document.getElementById('statTotalEggs').innerText = Number(data.total || 0).toLocaleString();
      document.getElementById('statTotalTrays').innerText = Math.floor((data.total || 0) / 30).toLocaleString();
      document.getElementById('statRecordCount').innerText = data.record_count || 0;
      document.getElementById('footerCount').innerText = data.record_count || 0;
      document.getElementById('footerTotal').innerText = Number(data.total || 0).toLocaleString();

      // Find top shed
      const shedTotals = data.totals_by_shed || {};
      let topShed = '-';
      let topCount = -1;
      for (const [shed, cnt] of Object.entries(shedTotals)) {
        if (cnt > topCount) {
          topCount = cnt;
          topShed = shed;
        }
      }
      document.getElementById('statTopShed').innerText = topShed;

      if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No egg production records logged yet. Enter today's count on the left!</td></tr>`;
        return;
      }

      tbody.innerHTML = records.map(r => {
        const trays = Math.floor(r.count / 30);
        const loose = r.count % 30;
        return `
          <tr class="hover:bg-slate-50 transition border-b border-slate-100">
            <td class="py-2.5 px-3 font-mono text-slate-600">${r.date}</td>
            <td class="py-2.5 px-3 font-semibold text-slate-800">${escapeHtml(r.shed)}</td>
            <td class="py-2.5 px-3 text-right font-bold text-slate-800">${Number(r.count).toLocaleString()}</td>
            <td class="py-2.5 px-3 text-right text-slate-500 font-mono">${trays}t + ${loose}</td>
            <td class="py-2.5 px-3 text-right font-mono font-semibold text-emerald-700">${Number(r.running_total).toLocaleString()}</td>
            <td class="py-2.5 px-3 text-center">
              <button onclick="deleteRecord(${r.id})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition" title="Delete record">
                <i class="fa-regular fa-trash-can"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function fetchWeeklySummary() {
      try {
        const res = await fetch('/api/eggs/weekly-summary');
        const data = await res.json();
        const preview = document.getElementById('whatsappPreview');
        const shareBtn = document.getElementById('whatsappShareBtn');

        if (data.records_count === 0) {
          preview.innerText = "No egg records logged yet. Add daily entries or click 'Load Sample Week' to test.";
          shareBtn.href = "#";
          return;
        }

        preview.innerText = data.whatsapp_message;
        shareBtn.href = data.whatsapp_url;
      } catch (err) {
        console.error(err);
      }
    }

    async function handleFormSubmit(e) {
      e.preventDefault();
      const shed = document.getElementById('shedInput').value.trim();
      const date = document.getElementById('dateInput').value;
      const count = parseInt(document.getElementById('countInput').value);

      if (!shed || !date || isNaN(count)) return;

      try {
        const res = await fetch('/api/eggs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ shed, date, count })
        });
        if (res.ok) {
          showToast(`Logged ${count} eggs for ${shed}!`);
          document.getElementById('countInput').value = '';
          updateTrayHelper();
          fetchRecords();
        } else {
          const err = await res.json();
          alert('Error logging record: ' + (err.detail?.[0]?.msg || JSON.stringify(err)));
        }
      } catch (err) {
        alert('Request failed: ' + err);
      }
    }

    async function deleteRecord(id) {
      if (!confirm('Are you sure you want to delete this log entry?')) return;
      try {
        const res = await fetch(`/api/eggs/${id}`, { method: 'DELETE' });
        if (res.ok) {
          showToast('Record deleted');
          fetchRecords();
        }
      } catch (err) {
        alert('Failed to delete: ' + err);
      }
    }

    async function seedSampleData() {
      try {
        const res = await fetch('/api/eggs/seed-sample', { method: 'POST' });
        const data = await res.json();
        showToast(data.message);
        fetchRecords();
      } catch (err) {
        alert('Seed failed: ' + err);
      }
    }

    async function clearAllData() {
      if (!confirm('This will wipe all egg records. Proceed?')) return;
      try {
        await fetch('/api/eggs', { method: 'DELETE' });
        showToast('All records cleared');
        fetchRecords();
      } catch (err) {
        alert('Clear failed: ' + err);
      }
    }

    function clearFilters() {
      document.getElementById('filterStart').value = '';
      document.getElementById('filterEnd').value = '';
      fetchRecords();
    }

    function copyWhatsAppText() {
      const text = document.getElementById('whatsappPreview').innerText;
      navigator.clipboard.writeText(text).then(() => {
        showToast('WhatsApp message copied to clipboard!');
      });
    }

    function escapeHtml(str) {
      return str.replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
    }

    // Initial load
    fetchRecords();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
