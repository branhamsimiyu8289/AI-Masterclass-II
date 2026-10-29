import os
import sys
import httpx
from google import genai
from dotenv import load_dotenv


MODEL = "gemini-3.5-flash-lite"


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Add it to a .env file or your environment.",
            file=sys.stderr,
        )
        return 1

    question = input("Welcome to Gemini AI Q&A! Ask me anything: ").strip()
    if not question:
        print("Please enter a question.", file=sys.stderr)
        return 1

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=genai.types.HttpOptions(
                timeout=60_000,
                retry_options=genai.types.HttpRetryOptions(attempts=1),
            ),
        )
        print("Gemini is thinking...", flush=True)
        response = client.interactions.create(
            model=MODEL,
            input=question,
            generation_config={"thinking_level": "minimal"},
            timeout=60,
        )
        answer = response.output_text
        if not answer:
            print("Gemini completed the request without returning text.", file=sys.stderr)
            return 1
        print("\nAnswer:")
        print(answer)
    except genai.errors.APIError as error:
        message = error.message or "The service returned an error."
        print(f"Gemini API error ({error.code}): {message}", file=sys.stderr)
        return 1
    except httpx.TimeoutException:
        print("Gemini did not respond within 60 seconds. Please try again.", file=sys.stderr)
        return 1
    except httpx.RequestError:
        print(
            "Could not connect to Gemini. Check your internet connection and try again.",
            file=sys.stderr,
        )
        return 1
    except TimeoutError:
        print("Gemini took too long to respond. Please try again.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())