"""
Egg Production Tracker - Full Stack Web Application
===================================================
A Flask REST API with an interactive browser interface for Kiambu poultry farmers.
Allows logging daily egg production per shed, computing weekly running totals,
and viewing real-time updates via JavaScript fetch() without page reload.
"""

from datetime import datetime
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# In-memory storage for egg production records
egg_records = []
_next_id = 1


@app.route("/")
def index():
    """Renders the browser interface for the farm manager."""
    return render_template("index.html")


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
    global _next_id

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

    record = {
        "id": _next_id,
        "shed_name": shed_name.strip(),
        "date": formatted_date,
        "count": count
    }
    _next_id += 1
    egg_records.append(record)

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
    records_with_running_total = []
    running_total = 0
    shed_totals = {}

    for rec in egg_records:
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
    """Optional endpoint to reset in-memory data during testing."""
    global _next_id
    egg_records.clear()
    _next_id = 1
    return jsonify({"message": "All egg records cleared successfully."}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
