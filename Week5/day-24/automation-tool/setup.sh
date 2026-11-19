#!/usr/bin/env bash
# ===================================================================
# Zawadi Sales Reporter - 1-Step Setup for Linux & macOS (Cron)
# ===================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  Zawadi Sales Reporter - Automated Cron Setup (Unix)  "
echo "========================================================"

python3 setup_scheduler.py --install
echo ""
python3 setup_scheduler.py --status
echo ""
echo "[+] Setup complete! Automation is now active."
