# Eldoret Hardware Customer Balance Lookup

## What this is

A small Flask web app for checking customer credit balances at a hardware shop
in Eldoret. It uses sample customer data stored in a Python dictionary.

## Problem

When credit sales and customer balances are tracked only in a notebook, looking
up how much a customer owes can take time and make it easy to misread a record.

## Solution

Enter a customer's name in the web form to look up their outstanding balance.
The app also provides a JSON API for retrieving a balance by customer name.
Names are matched without regard to letter case. The sample data is hardcoded,
so balances are for demonstration and are not saved between app changes.

## Run the app

From this `day-16` folder, install Flask if it is not already installed:

```powershell
python -m pip install Flask
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser. To look up a
balance directly, visit
`http://127.0.0.1:5000/api/balance?name=Branham%20Simiyu`.

## Example output

Searching for `Branham Simiyu` in the web form displays:

```text
Branham Simiyu owes KES 12,500.
```

The API returns:

```json
{
  "balance": 12500,
  "currency": "KES",
  "customer": "Branham Simiyu"
}
```

An unknown customer receives a JSON error with HTTP status `404`; omitting the
name returns a JSON error with HTTP status `400`.

## Features and technologies

- Flask routes serving an HTML search page and a JSON balance API
- In-memory Python dictionary containing five sample customer balances
- Case-insensitive customer name lookup and URL-encoded query parameter
- HTML, CSS, and JavaScript form that fetches and displays API results
- Input and unknown-customer error responses

## I would charge a hardware shop owner KES 5,000 for this tool.

## Author

Branham Simiyu
