import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
SYSTEM_PROMPT = """Extract property inquiry details from the customer's message.
Return a JSON object with exactly these fields:
- property_type: property type, such as house, apartment, or bedsitter; null if missing
- bedrooms: number of bedrooms as an integer; null if missing or not stated
- location: requested neighborhood or area; null if missing
- budget_kes: budget in Kenyan shillings as an integer; null if missing
- rental_or_sale: "rental" or "sale"; null if unclear

Convert shorthand such as "80k" to 80000. Do not guess missing details.
Return only JSON matching the required schema.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "property_type": {"type": "STRING", "nullable": True},
        "bedrooms": {"type": "INTEGER", "nullable": True},
        "location": {"type": "STRING", "nullable": True},
        "budget_kes": {"type": "INTEGER", "nullable": True},
        "rental_or_sale": {
            "type": "STRING",
            "enum": ["rental", "sale"],
            "nullable": True,
        },
    },
    "required": [
        "property_type",
        "bedrooms",
        "location",
        "budget_kes",
        "rental_or_sale",
    ],
}

DEMO_INQUIRIES = (
    "I am looking for a 3-bedroom house in Kileleshwa, budget around 80k per month",
    "Do you have any bedsitters near Westlands under 20k?",
    "I am interested in buying an apartment in Kilimani.",
)

FIELD_NAMES = (
    "property_type",
    "bedrooms",
    "location",
    "budget_kes",
    "rental_or_sale",
)


def extract_property_details(
    client: genai.Client, inquiry: str
) -> dict[str, object | None]:
    response = client.models.generate_content(
        model=MODEL,
        contents=inquiry,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0,
        ),
    )
    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    details = json.loads(response.text)
    if not isinstance(details, dict) or set(details) != set(FIELD_NAMES):
        raise ValueError("Gemini returned JSON with an unexpected set of fields.")
    string_fields = ("property_type", "location")
    integer_fields = ("bedrooms", "budget_kes")
    for field in string_fields:
        value = details[field]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"Gemini returned an invalid {field} value.")
    for field in integer_fields:
        value = details[field]
        if value is not None and type(value) is not int:
            raise ValueError(f"Gemini returned an invalid {field} value.")
    if details["rental_or_sale"] not in (None, "rental", "sale"):
        raise ValueError('rental_or_sale must be "rental", "sale", or null.')
    return details


def print_property_details(details: dict[str, object | None]) -> None:
    for field in FIELD_NAMES:
        value = details[field]
        display_value = "Not provided" if value is None else str(value)
        print(f"{field}: {display_value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract property details from a customer inquiry with Gemini."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="process three sample inquiries, including one with missing details",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Set it in your environment or Week3 .env file.",
            file=sys.stderr,
        )
        return 1

    if args.demo:
        inquiries = DEMO_INQUIRIES
    else:
        inquiry = input("Enter the property inquiry: ").strip()
        if not inquiry:
            print("Please enter a property inquiry.", file=sys.stderr)
            return 1
        inquiries = (inquiry,)

    client = genai.Client(api_key=api_key)
    for index, inquiry in enumerate(inquiries, start=1):
        if args.demo:
            print(f"\nInquiry {index}: {inquiry}")
        try:
            details = extract_property_details(client, inquiry)
        except json.JSONDecodeError as error:
            print(f"Gemini returned invalid JSON: {error}", file=sys.stderr)
            return 1
        except ValueError as error:
            print(f"Could not extract property details: {error}", file=sys.stderr)
            return 1
        except genai.errors.APIError as error:
            message = error.message or "The Gemini service returned an error."
            print(f"Gemini API error ({error.code}): {message}", file=sys.stderr)
            return 1
        except httpx.TimeoutException:
            print("Gemini did not respond in time. Please try again.", file=sys.stderr)
            return 1
        except httpx.RequestError:
            print(
                "Could not connect to Gemini. Check your internet connection and try again.",
                file=sys.stderr,
            )
            return 1

        print_property_details(details)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
