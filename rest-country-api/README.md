# REST Countries CLI

A small Python command-line application that looks up a country using the
[REST Countries API](https://restcountries.com/docs/countries). Enter a
country name in the terminal to view its common name, capital, population,
and currency code(s).

## Features

- Prompts for a country name in the terminal.
- Looks up country data through the REST Countries v5 API.
- Displays the country's common name, capital, population, and currency code(s).
- Reads the API bearer token from a local `.env` file instead of hard-coding it.
- Handles blank input, missing API data, and request failures with messages.

## Project structure

```text
rest-country-api/
├── day1-api.py   # CLI entry point and API request/response handling
├── .env          # Local API key; create this yourself and keep it private
├── .gitignore    # Excludes .env files from Git
└── README.md     # Project documentation
```

## Requirements

- Python 3.8 or newer
- A REST Countries API key
- `requests`
- `python-dotenv`

Install the Python dependencies:

```bash
python -m pip install requests python-dotenv
```

## Setup

1. Get an API key from the [REST Countries API](https://restcountries.com/api-keys).
2. Create a `.env` file in the same directory as `day1-api.py`.
3. Add your key using this variable name:

   ```dotenv
   RESTCOUNTRIES_API_KEY=replace_with_your_api_key
   ```

   Do not commit or share this file. The repository's `.gitignore` excludes it.

## Run

From the project directory, run:

```bash
python day1-api.py
```

Enter a country when prompted and press Enter:

```text
=======REST COUNTRY APIs=======
Enter a country: Uganda
Country:    Uganda
Capital:    Kampala
Population: <value returned by the API>
Currency:   UGX
```

The population shown by a real request comes from the API and may change as its
data is updated. To look up another country, enter its name at the prompt.

## System flow

```text
Start program
    ↓
Load .env from the script's directory
    ↓
Read RESTCOUNTRIES_API_KEY
    ↓
Prompt for a country name
    ↓
Build and send an authenticated request to the v5 API
    ↓
Check the response and parse data.objects
    ↓
Print country details, or a helpful no-data/request error message
```

## Architecture

This is a single-script CLI application:

- **Configuration:** `python-dotenv` loads the API key from `.env`; `os.getenv`
  reads it without exposing it in source code.
- **Input and presentation:** Python's `input()` reads the country name, and
  `print()` displays the result in the terminal.
- **API client:** `requests` sends an HTTP GET request to the REST Countries
  v5 country-name endpoint with a Bearer authorization header and timeout.
- **Response handling:** The script checks the response, reads the
  `data.objects` records, and extracts the fields it displays.

## Technologies used

- Python
- [Requests](https://requests.readthedocs.io/) for HTTP requests
- [python-dotenv](https://github.com/theskumar/python-dotenv) for `.env` loading
- REST Countries API v5 for country data

## Learning focus

- Reading terminal input and validating blank values
- Loading configuration and protecting API credentials
- Making authenticated HTTP requests
- Handling request errors and JSON response data
- Accessing nested dictionaries and lists safely
- Formatting numbers and printing a simple CLI result

## Author

**Branham Simiyu**
