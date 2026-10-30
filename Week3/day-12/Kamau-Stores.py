import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
SYSTEM_PROMPT = """You are a customer service assistant for Kamau Stores,
a wholesale distributor in Nairobi.

Your rules:
- Only answer questions about orders, pricing, and delivery.
- All prices are in KES. Never mention USD.
- Delivery covers Nairobi, Mombasa, Kisumu, and Nakuru only.
- If a question is outside your scope, say: "Please call our office
  on 0712 345 678 for that."
- Always be polite and professional. End every answer with
  "Asante kwa kuwasiliana."

Examples:
Customer: "Do you deliver to Nakuru?"
Answer: "Yes, we deliver to Nakuru. Asante kwa kuwasiliana."

Customer: "Do you deliver to Eldoret?"
Answer: "Please call our office on 0712 345 678 for that.
Asante kwa kuwasiliana."

"""


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Set it in your environment or Week3 .env file.",
            file=sys.stderr,
        )
        return 1

    question = input("Welcome to Kamau Stores. How can we help? ").strip()
    if not question:
        print("Please enter a question.", file=sys.stderr)
        return 1

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=512,
            ),
        )
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

    answer = response.text
    if not answer:
        print("Gemini did not return a text response.", file=sys.stderr)
        return 1

    print(f"\n{answer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
