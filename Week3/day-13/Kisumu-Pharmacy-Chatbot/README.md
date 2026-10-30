# Kisumu Pharmacy Chatbot

A command-line assistant that helps Kisumu Pharmacy staff respond consistently
to common customer questions. It uses Gemini to answer questions about opening
hours and pharmacy services, understand follow-up questions in the same
conversation, and direct clinical or uncertain requests to the pharmacist
instead of guessing.

## Features

- Lists pharmacy opening hours: Monday to Saturday, 8:00 AM–8:00 PM; Sunday,
  10:00 AM–4:00 PM.
- Covers prescription dispensing, repeat prescriptions, over-the-counter
  medicine support, medication-use counselling, processing updates, stock
  availability, and refills.
- Maintains conversation context so follow-up questions can refer to earlier
  messages.
- Avoids inventing medicine stock, processing times, prices, or prescription
  document requirements.
- Refers clinical questions to the pharmacist.

## Requirements

- Python 3.10 or later
- A Gemini API key
- `google-genai`, `python-dotenv`, and `httpx`

## Setup

Install the required packages:

```powershell
python -m pip install google-genai python-dotenv httpx
```

Set `GEMINI_API_KEY` in your environment, or add it to the `Week3/.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

Keep your API key private and do not commit `.env` to source control.

## Run

From the `Week3` directory:

```powershell
python .\day-13\Kisumu-Pharmacy-Chatbot\pharmacy-chatbot.py
```

Enter questions at the `Staff:` prompt. Type `exit` to end the session.

## Example conversation

See [example.txt](./example.txt) for a sample exchange, including a follow-up
about a customer's blood sugar concern.
