# Proposal Feedback Tool

A command-line tool that uses Google Gemini to help freelancers strengthen
client proposals. It returns one specific strength, one actionable improvement,
and a clearer rewrite of the opening sentence. Suggestions are guidance only;
review them to ensure they accurately represent your work.

## Requirements

- Python 3.10+
- A [Gemini API key](https://aistudio.google.com/apikey)
- An internet connection

## Setup

From this directory, create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install google-genai python-dotenv httpx
```

On macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install google-genai python-dotenv httpx
```

Set `GEMINI_API_KEY` in your environment or create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

The `.env` file is excluded from Git. Keep your API key private.

## Usage

Run without arguments to paste a multi-line proposal. Enter `END` on its own
line to submit:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

On macOS or Linux, run `.venv/bin/python main.py`.

To pass proposal text directly:

```powershell
.\.venv\Scripts\python.exe .\main.py "I can build your booking website using Python and React."
```

Use `.venv/bin/python main.py "Your proposal"` on macOS or Linux.

## Privacy

Proposal text is sent to Google's Gemini API for review. Avoid including
confidential client details or other sensitive information. Verify suggestions
before using them.

**Author:** [Branham Simiyu](https://github.com/branhamsimiyu8289)
