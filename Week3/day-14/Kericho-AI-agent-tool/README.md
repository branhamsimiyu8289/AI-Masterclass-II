# Kericho Tea Harvesting Agent

A command-line Gemini agent for a tea estate field supervisor. Ask a question
about the weather or harvesting and it fetches current conditions and the
hourly rain forecast for the estate before giving practical advice.

## Harvesting rules

The agent follows these rules, included in its Gemini system prompt:

- Good conditions: no rain in the next 6 hours, temperature from 15°C through
  25°C, and relative humidity below 60%.
- Bad conditions: active rain or temperature above 28°C; postpone harvesting.
- Otherwise, report mixed conditions and explain what to monitor.

The default coordinates represent Kericho town. For a more precise estate
forecast, set `ESTATE_LATITUDE` and `ESTATE_LONGITUDE` to the estate's
coordinates.

## Requirements

- Python 3.10 or later
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- `google-genai`, `python-dotenv`, and `httpx`

Open-Meteo provides weather data without a separate API key.

## Setup

From the `AI-Masterclass-II` repository root, install the packages in the
existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install google-genai python-dotenv httpx
```

Add your Gemini key to `Week3\.env`:

```env
GEMINI_API_KEY=your_api_key_here
```

Optionally add the estate's GPS coordinates to the same file:

```env
ESTATE_LATITUDE=-0.3676
ESTATE_LONGITUDE=35.2830
```

Keep API keys private.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe .\Week3\day-14\Kericho-AI-agent-tool\agent-tool.py
```

Example question:

```text
Ask about Kericho weather or tea harvesting: Is today good for harvesting?
Gemini is thinking...
Calling get_kericho_weather...

Recommendation:
Rain is expected later this morning, so harvesting conditions are not ideal.
Postpone plucking and check the forecast again after the rain passes.
```

Gemini's wording and the recommendation depend on the live weather data.

## Tests

Run the unit tests from this folder:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_agent_tool.py
```

The tests mock Gemini and the weather API. They check a harvesting question
that calls the weather tool and two questions that do not.
