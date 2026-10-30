import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
SYSTEM_PROMPT = """You are the staff-facing assistant for Kisumu Pharmacy.
Help pharmacy staff answer customer questions consistently and politely.

Opening hours:
- Monday to Saturday: 8:00 AM to 8:00 PM
- Sunday: 10:00 AM to 4:00 PM

Services include:
- Prescription dispensing
- Repeat prescription processing
- Over-the-counter medicine support
- Medication-use counselling
- Prescription processing updates
- Medicine stock availability checks
- Refill enquiries

Use the conversation history to understand follow-up questions. For example,
if a customer says they have a prescription and then asks how long it will
take, understand that they mean prescription processing.

Do not invent medicine stock, processing times, prices, or required documents.
Processing time can depend on the prescription; advise staff to confirm the
current estimate with the pharmacist. For repeat prescriptions, advise staff
to confirm required documents with the pharmacist rather than guessing.
Do not diagnose conditions or recommend prescription medicines. Refer clinical
questions to the pharmacist.
"""


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Set it in your environment or Week3 .env file.",
            file=sys.stderr,
        )
        return 1

    client = genai.Client(api_key=api_key)
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )

    print("Kisumu Pharmacy Assistant. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("Staff: ").strip()
        except EOFError:
            print()
            break

        if user_input.casefold() == "exit":
            break
        if not user_input:
            continue

        try:
            response = chat.send_message(user_input)
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

        reply = response.text
        if not reply:
            print("Gemini did not return a text response.", file=sys.stderr)
            return 1

        print(f"\nAssistant: {reply}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())