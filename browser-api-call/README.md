# Country Info

Country Info is a small browser app for looking up country details using the
REST Countries API. Enter a country name to see its flag, common name, capital,
region, and population.

## Problem and solution

Finding basic facts about a country can require manually browsing reference
pages. This project provides a simple search page that retrieves and displays
country information from the REST Countries v5 API. A local Python server makes
the authenticated API request so the API key is not included in browser code.

## Requirements

- Python 3
- A valid REST Countries API key with access to API v5

## Configure the API key

Create a file named `.env` in this `browser-api-call` directory, beside
`server.py`. Add your key as:

```dotenv
RESTCOUNTRIES_API_KEY=your_real_api_key
```

Alternatively, set `RESTCOUNTRIES_API_KEY` in the environment before starting
the server. The environment variable takes precedence over `.env`.

Keep the key private. Do not paste it into source code, share it, or commit the
`.env` file.

## Run

In PowerShell, change to this directory and start the server:

```powershell
cd "C:\Users\owenc\OneDrive\Desktop\AI-Masterclass II\AI-Masterclass-II\browser-api-call"
py .\server.py
```

Leave that terminal open and visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
in your browser. Search for a country, such as `Kenya`. Do not open
`rest-country.html` directly; it needs the local server to proxy API requests.
Stop the server with `Ctrl+C`.

## Example

For a successful lookup of Kenya, the page displays the country's flag and
common name, along with its capital, region, and population. Exact data comes
from the API and may change.

The browser sends a request to the local endpoint:

```text
http://127.0.0.1:8000/api/country?name=Kenya
```

The server forwards the request to REST Countries and returns JSON to the page.

## Troubleshooting

- **Missing `.env` or `RESTCOUNTRIES_API_KEY` error:** Confirm `.env` is in
  `browser-api-call`, next to `server.py`, and that the variable has a nonempty
  value.
- **HTTP 401:** The API key is missing, invalid, or lacks access. Check it with
  the API provider; do not share it.
- **Could not connect:** Check your internet connection and confirm the server
  is still running in the terminal.
- **Port already in use:** Stop the other process using port `8000`, then
  restart this server.

## Features and technologies

- Country search page built with HTML, CSS, and JavaScript
- Python HTTP server serving the page and proxying API requests
- REST Countries API v5 for current country information
- API key loaded from a local `.env` file or environment variable
- Handles blank searches, API errors, and connection failures
