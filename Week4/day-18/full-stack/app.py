"""
Egg Production Tracker - Full Stack Web Application
===================================================
A Flask REST API with an interactive browser interface for Kiambu poultry farmers.
Allows logging daily egg production per shed, computing weekly running totals,
and viewing real-time updates via JavaScript fetch() without page reload.
"""

import hmac
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)
app.config["DATABASE_PATH"] = os.environ.get(
    "DATABASE_PATH", os.path.join(app.instance_path, "eggs.db")
)
app.config["RESET_TOKEN"] = os.environ.get("RESET_TOKEN")


@contextmanager
def database():
    """Open the configured SQLite database and ensure its schema exists."""
    database_path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS egg_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shed_name TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER NOT NULL CHECK (count >= 0)
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.route("/")
def index():
    """Renders the browser interface for the farm manager."""
    return render_template("index.html")


@app.route("/healthz")
def health_check():
    """Check that the application and its database are available."""
    with database() as db:
        db.execute("SELECT 1")
    return jsonify({"status": "ok"}), 200


@app.route("/api/eggs", methods=["POST"])
def log_egg_record():
    """
    Log a daily egg production record.
    Expected JSON payload:
    {
        "shed_name": "Shed 1",   # (or "shed")
        "date": "2026-11-11",    # YYYY-MM-DD
        "count": 145             # Non-negative integer
    }
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must be a valid JSON object."
        }), 400

    # Flexible key extraction for shed name: 'shed_name', 'shed', or 'shed name'
    shed_name = data.get("shed_name") or data.get("shed") or data.get("shed name")
    if not shed_name or not isinstance(shed_name, str) or not shed_name.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'shed_name' is required and must be a non-empty string."
        }), 400

    date_str = data.get("date")
    if not date_str or not isinstance(date_str, str):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'date' is required (expected format YYYY-MM-DD)."
        }), 400

    # Validate date format (YYYY-MM-DD)
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        formatted_date = parsed_date.isoformat()
    except ValueError:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid date format '{date_str}'. Expected YYYY-MM-DD."
        }), 400

    count = data.get("count")
    if count is None or isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'count' is required and must be a non-negative integer."
        }), 400

    with database() as db:
        cursor = db.execute(
            "INSERT INTO egg_records (shed_name, date, count) VALUES (?, ?, ?)",
            (shed_name.strip(), formatted_date, count),
        )
        record = {
            "id": cursor.lastrowid,
            "shed_name": shed_name.strip(),
            "date": formatted_date,
            "count": count,
        }

    return jsonify({
        "message": "Egg record logged successfully.",
        "record": record
    }), 201


@app.route("/api/eggs", methods=["GET"])
def get_egg_records():
    """
    Return all egg records, each with its cumulative running total,
    plus overall summary totals and per-shed breakdowns.
    """
    with database() as db:
        records = db.execute(
            "SELECT id, shed_name, date, count FROM egg_records ORDER BY id"
        ).fetchall()

    records_with_running_total = []
    running_total = 0
    shed_totals = {}

    for rec in records:
        running_total += rec["count"]
        shed_name = rec["shed_name"]
        shed_totals[shed_name] = shed_totals.get(shed_name, 0) + rec["count"]

        records_with_running_total.append({
            "id": rec["id"],
            "shed_name": shed_name,
            "date": rec["date"],
            "count": rec["count"],
            "running_total": running_total
        })

    return jsonify({
        "total_records": len(records_with_running_total),
        "total_eggs": running_total,
        "shed_breakdown": shed_totals,
        "records": records_with_running_total
    }), 200


@app.route("/api/eggs", methods=["DELETE"])
def reset_records():
    """Clear records only when a configured bearer token is supplied."""
    reset_token = app.config.get("RESET_TOKEN")
    if not reset_token:
        abort(404)

    authorization = request.headers.get("Authorization", "")
    supplied_token = authorization[7:] if authorization.startswith("Bearer ") else ""
    if not hmac.compare_digest(reset_token, supplied_token):
        return jsonify({"error": "Forbidden", "message": "A valid reset token is required."}), 403

    with database() as db:
        db.execute("DELETE FROM egg_records")
    return jsonify({"message": "All egg records cleared successfully."}), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
