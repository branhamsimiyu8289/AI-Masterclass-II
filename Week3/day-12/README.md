# Day 12: Property Inquiry Extraction

`day-12-exercise.py` is a Gemini-powered property inquiry extractor for a
Nairobi property agent. It solves the problem of manually reading WhatsApp
messages and copying details into a spreadsheet by extracting each inquiry
into consistent fields, while marking missing details instead of guessing.

## Extracted fields

- `property_type`: The kind of property, such as a house, apartment, or
  bedsitter. This helps the agent match the inquiry to the right listings.
- `bedrooms`: The requested bedroom count, useful for narrowing the search.
- `location`: The requested neighborhood or area, which identifies where to
  find suitable properties.
- `budget_kes`: The customer's budget in Kenyan shillings, used to filter
  affordable options. Shorthand such as `80k` is converted to `80000`.
- `rental_or_sale`: Whether the customer wants to rent or buy, so rental and
  sale listings are not mixed.

## Setup

The script uses the Gemini API key from the `GEMINI_API_KEY` environment
variable or the `Week3/.env` file. Keep the key private.

Install the required packages in your Python environment if they are not
already installed:

```powershell
python -m pip install google-genai python-dotenv httpx
```

## Run

From the `Week3` folder, enter a single inquiry:

```powershell
python .\day-12\day-12-exercise.py
```

Run the three example inquiries, including one with missing bedroom and budget
information:

```powershell
python .\day-12\day-12-exercise.py --demo
```

## Sample output

The exact output can vary with the inquiry, but a demo run looks like this:

```text
Inquiry 1: I am looking for a 3-bedroom house in Kileleshwa, budget around 80k per month
property_type: house
bedrooms: 3
location: Kileleshwa
budget_kes: 80000
rental_or_sale: rental

Inquiry 2: Do you have any bedsitters near Westlands under 20k?
property_type: bedsitter
bedrooms: Not provided
location: Westlands
budget_kes: 20000
rental_or_sale: rental

Inquiry 3: I am interested in buying an apartment in Kilimani.
property_type: apartment
bedrooms: Not provided
location: Kilimani
budget_kes: Not provided
rental_or_sale: sale
```
