#!/usr/bin/env bash
# ==============================================================================
# Invoice Reminder Automation Service - Shell Runner (Linux / macOS)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================================================="
echo "       INVOICE REMINDER AUTOMATION SERVICE - CLIENT DISPATCH RUNNER"
echo "=============================================================================="
echo ""

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python was not found in your PATH."
    exit 1
fi

"$PYTHON_CMD" invoice_reminder.py "$@"

echo ""
echo "=============================================================================="
echo "Process completed. Drafted emails are saved in the Outbox/ directory."
echo "=============================================================================="
