# Kamau Stores Gemini AI Agent

A command-line shopping assistant that uses Google's Gemini to answer questions
about Kamau Stores' sample stock levels and product prices.

## What it is

The agent gives Gemini two tools: look up a product's stock and look up its
price per bag. When a question needs store information, Gemini chooses a tool,
the program runs the matching lookup, and the result is sent back to Gemini to
write a natural-language answer.

## What problem it solves

Instead of manually checking sample inventory and price lists, a user can ask
questions in everyday language, such as whether an item is in stock or how much
it costs. The agent can handle both lookups in one question and reports when a
product is not found.

The inventory and prices are sample data stored in the script, not a live store
database. Stock is listed for maize flour, wheat flour, rice, sugar, and cooking
oil. Prices are listed for maize flour, wheat flour, and rice.

## Requirements

- Python 3.10 or later
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- The `google-genai`, `python-dotenv`, and `httpx` Python packages

## Setup

Open PowerShell at the `AI-Masterclass-II` repository root. Create a virtual
environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install google-genai python-dotenv httpx
```

Create `Week3\.env` and add your API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Keep the key private. The agent reads this file automatically, or you can set
`GEMINI_API_KEY` in your environment instead.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe .\Week3\day-14\ai-agents.py
```

Enter a question when prompted. For example:

```text
Ask Kamau Stores about stock or prices: Do you have maize flour, and how much is a bag of rice?
Gemini is thinking...
Calling get_stock_level...
Calling get_price...

Answer:
Yes, there are 120 bags of maize flour in stock. A bag of rice costs KES 4,500.
```

Gemini's wording may vary. The agent uses the `gemini-3.5-flash-lite` model and
reports API, connection, timeout, and agent errors in the terminal.
