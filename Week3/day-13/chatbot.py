import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
SYSTEM_PROMPT = """You are an assistant for Otieno Wholesale in Kisumu.
Answer questions about stock, pricing, and delivery.
All prices are in KES. Be helpful and brief."""


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Set it in your environment or Week3 .env file.",
            file=sys.stderr,
        )
        return 1

    client = genai.Client(api_key=api_key)
    chat_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
    )
    chat = client.chats.create(model=MODEL, config=chat_config)
    messages: list[dict[str, str]] = []

    print("Otieno Wholesale Assistant. Type 'exit' to quit.\n")
    exit_code = 0

    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            print()
            break

        if user_input.casefold() == "exit":
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = chat.send_message(user_input)
        except genai.errors.APIError as error:
            message = error.message or "The Gemini service returned an error."
            print(f"Gemini API error ({error.code}): {message}", file=sys.stderr)
            exit_code = 1
            break
        except httpx.TimeoutException:
            print("Gemini did not respond in time. Please try again.", file=sys.stderr)
            exit_code = 1
            break
        except httpx.RequestError:
            print(
                "Could not connect to Gemini. Check your internet connection and try again.",
                file=sys.stderr,
            )
            exit_code = 1
            break

        reply = response.text
        if not reply:
            print("Gemini did not return a text response.", file=sys.stderr)
            exit_code = 1
            break

        messages.append({"role": "assistant", "content": reply})
        print(f"\nAssistant: {reply}\n")

        history = chat.get_history()
        if len(history) > 10:
            chat = client.chats.create(
                model=MODEL,
                config=chat_config,
                history=history[-10:],
            )

    log = {
        "date": datetime.now().isoformat(),
        "messages": messages,
    }
    log_path = Path(__file__).with_name("chat_log.json")
    try:
        log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as error:
        print(f"Could not save conversation log to {log_path}: {error}", file=sys.stderr)
        return 1

    print(f"Conversation saved to {log_path.name}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
