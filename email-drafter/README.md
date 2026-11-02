# Gemini Email Drafter

This command-line app uses Google's Gemini AI to draft concise, warm,
professional Kenyan business emails from a topic you provide. For example, give
it a topic like “follow up on an unpaid invoice” and it will return an email
draft. Review the draft and replace any details or placeholders before sending.

## What you need

- Python 3.10 or later
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- An internet connection

## Install

Open a terminal in this `email-drafter` folder.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install google-genai python-dotenv httpx
```

### macOS or Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install google-genai python-dotenv httpx
```

Create a file named `.env` in this folder and add your API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your key. Keep the key private: do not paste it
into the Python file, share it, or commit the `.env` file. This folder's
`.gitignore` excludes `.env` and the local virtual environment.

## Use

Run the app from this folder. With no arguments, it asks for the topic:

### Windows (PowerShell)

```powershell
.\.venv\Scripts\python.exe .\email-drafter.py
```

### macOS or Linux

```bash
.venv/bin/python email-drafter.py
```

At the prompt, type a topic and press Enter. You can also pass the topic
directly as a command-line argument:

### Windows (PowerShell)

```powershell
.\.venv\Scripts\python.exe .\email-drafter.py "Request a meeting next week"
```

### macOS or Linux

```bash
.venv/bin/python email-drafter.py "Request a meeting next week"
```

The generated draft appears in the terminal. If the key is missing or Gemini
returns an API, connection, or timeout error, the app prints an error message.

## What it costs

The email-drafter program and the Python packages are free. Gemini API usage
may be free within Google's current free-tier limits, or may incur charges on
a paid tier. Charges depend on the selected model and the number of input and
output tokens; each draft sends a request to Gemini. Google can change model
availability, free-tier limits, and prices, so check the
[Gemini API pricing page](https://ai.google.dev/gemini-api/docs/pricing) for
the current terms before use. You can also review usage and billing in your
Google AI Studio or Google Cloud account.

Do not include sensitive or confidential information in a prompt unless you
have checked the applicable Google data-use terms for your API tier.
