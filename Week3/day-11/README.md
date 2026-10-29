# Gemini AI Q&A

A small command-line program that sends one question to Google's Gemini API and
prints the response.

## Requirements

- Python
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

Open PowerShell in this project folder and create a virtual environment:

```powershell
uv venv .venv
uv pip install --python .\.venv\Scripts\python.exe google-genai python-dotenv httpx
```

Create a `.env` file in this folder with your API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Keep the key private. The `.gitignore` in this folder prevents `.env` and the
virtual environment from being committed.

## Run

```powershell
.\.venv\Scripts\python.exe .\geminai.py
```

Enter a question when prompted. The script uses the `gemini-3.5-flash-lite`
model with minimal reasoning. API errors, connection failures, and timeouts are
reported in the terminal.
