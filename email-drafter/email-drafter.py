import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
SYSTEM_PROMPT = (
    "You write professional Kenyan business emails. "
    "Keep them concise, warm, and direct. "
    "Format the email with a blank line between the greeting, each focused "
    "body paragraph, and the closing and signature. Avoid long blocks of text. "
    "Use a short bullet list only when it makes details easier to scan, and "
    "leave a blank line before and after the list."
)


def draft_email(topic: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to email-drafter/.env "
            "or set it in your environment."
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Write a professional email about: {topic}",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    if not response.text:
        raise RuntimeError("Gemini returned no email text.")
    return response.text


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    if len(sys.argv) < 2:
        try:
            topic = input("What should the email be about? ").strip()
        except EOFError:
            print("\nNo email topic was entered.", file=sys.stderr)
            sys.exit(1)
    else:
        topic = " ".join(sys.argv[1:]).strip()

    if not topic.strip():
        print("Please provide an email topic.", file=sys.stderr)
        sys.exit(1)

    try:
        print(draft_email(topic))
    except genai.errors.APIError as error:
        message = error.message or "The Gemini service returned an error."
        print(f"Gemini API error ({error.code}): {message}", file=sys.stderr)
        sys.exit(1)
    except httpx.TimeoutException:
        print("Gemini did not respond in time. Please try again.", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError:
        print(
            "Could not connect to Gemini. Check your internet connection and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)