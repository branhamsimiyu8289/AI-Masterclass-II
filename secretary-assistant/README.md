# Thika Matatu SACCO Assistant

A command-line assistant that uses Google's Gemini API to answer common member
questions about account balances, meeting times, and membership fees. The sample
operational details in the system prompt are fictional demonstration values;
replace them with verified SACCO information before real use.

## Requirements

- Python 3.10 or later
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- `uv` for environment and dependency setup

## Setup on Windows

Open PowerShell in this project folder and run:

```powershell
uv venv .venv
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `GEMINI_API_KEY` to your own key. Do not share the key or
commit `.env`.

## Run

Ask one member question:

```powershell
.\.venv\Scripts\python.exe .\assistant.py
```

Run the six built-in example questions:

```powershell
.\.venv\Scripts\python.exe .\assistant.py --demo
```

The demo covers multiple phrasings of balances, meeting schedules, and fees.
The program reports API, timeout, and connection errors in the terminal.
