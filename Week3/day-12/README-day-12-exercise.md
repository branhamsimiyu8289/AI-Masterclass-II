# Day 12 Exercise: Property Inquiry Extractor

This script uses the Google Gemini API to extract structured property details from a customer inquiry.

It is designed to parse messages such as:

- property type (house, apartment, bedsitter, etc.)
- number of bedrooms
- location
- budget in KES
- whether the inquiry is rental or sale

The output is returned as JSON with a strict schema.

## Features

- Extracts key property details from natural-language inquiries
- Uses a fixed JSON schema for consistent output
- Accepts shorthand values like `80k` and converts them to `80000`
- Supports a demo mode with sample inquiries
- Validates that the response matches the expected structure

## Requirements

- Python 3.9 or later
- A valid Gemini API key
- Internet access for the Google GenAI API

## Install dependencies

```bash
pip install httpx python-dotenv google-genai
```

## Environment setup

Create a `.env` file in the `Week3` directory:

```env
GEMINI_API_KEY=your_api_key_here
```

The script loads the environment file from:

```text
Week3/.env
```

## Run the script

From the project root:

```bash
python "Week3/day-12/day-12-exercise.py"
```

### Demo mode

```bash
python "Week3/day-12/day-12-exercise.py" --demo
```

This runs three sample property inquiries and prints the extracted details.

## Example input

```text
I am looking for a 3-bedroom house in Kileleshwa, budget around 80k per month
```

## Example output

```json
{
  "property_type": "house",
  "bedrooms": 3,
  "location": "Kileleshwa",
  "budget_kes": 80000,
  "rental_or_sale": "rental"
}
```

## Notes

- Missing values are returned as `null`.
- The script does not guess details that are not provided.
- Only JSON matching the required schema is accepted.

## File

- `Week3/day-12/day-12-exercise.py`
