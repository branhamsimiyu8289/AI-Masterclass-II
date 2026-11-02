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
SYSTEM_PROMPT = (
    "You are a constructive editor helping freelance developers improve "
    "short client proposals. Evaluate only the proposal provided. Identify "
    "its single strongest point and its single most important weakness. "
    "Rewrite only the opening sentence to make it clearer and more compelling. "
    "Keep the rewrite truthful to the proposal; do not invent experience, "
    "skills, or promises. Be specific, concise, and encouraging."
)
FEEDBACK_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "strength": types.Schema(
            type=types.Type.STRING,
            description="One specific strength in the proposal.",
        ),
        "weakness": types.Schema(
            type=types.Type.STRING,
            description="One specific, actionable weakness in the proposal.",
        ),
        "rewritten_opening_sentence": types.Schema(
            type=types.Type.STRING,
            description="A truthful, improved version of the proposal's opening sentence.",
        ),
    },
    required=["strength", "weakness", "rewritten_opening_sentence"],
)


def read_proposal() -> str:
    print("Paste your proposal below. Enter END on a line by itself when finished:")
    lines: list[str] = []
    for line in sys.stdin:
        line = line.rstrip("\r\n")
        if line.strip().casefold() == "end":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def review_proposal(proposal: str) -> dict[str, str]:
    if not proposal.strip():
        raise RuntimeError("Please provide a proposal to review.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to proposal-feedback-tool/.env "
            "or set it in your environment."
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Review this freelance proposal:\n\n{proposal}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=FEEDBACK_SCHEMA,
        ),
    )
    if not response.text or not response.text.strip():
        raise RuntimeError("Gemini returned no feedback.")

    try:
        feedback = json.loads(response.text)
    except json.JSONDecodeError as error:
        raise RuntimeError("Gemini returned feedback in an invalid format.") from error

    fields = ("strength", "weakness", "rewritten_opening_sentence")
    if not isinstance(feedback, dict) or any(
        not isinstance(feedback.get(field), str) or not feedback[field].strip()
        for field in fields
    ):
        raise RuntimeError("Gemini returned incomplete proposal feedback.")
    return {field: feedback[field].strip() for field in fields}


def _api_error_message(error: genai.errors.APIError) -> str:
    message = error.message or ""
    normalized_message = message.casefold()
    status = (error.status or "").upper()
    invalid_key = (
        error.code in (401, 403)
        or status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}
        or (
            "api key" in normalized_message
            and any(term in normalized_message for term in ("invalid", "not valid"))
        )
    )
    if invalid_key:
        return (
            "Gemini rejected the API key or its permissions. Check "
            "GEMINI_API_KEY in your .env file or environment."
        )

    detail = message or "The Gemini service returned an error."
    return f"Gemini API error ({error.code}): {detail}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Get one strength, one weakness, and a rewritten opening sentence "
            "for a freelance proposal."
        )
    )
    parser.add_argument(
        "proposal",
        nargs="*",
        help="Proposal text; omit it to paste a multi-line proposal interactively.",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().with_name(".env"))
    proposal = " ".join(args.proposal).strip() if args.proposal else read_proposal()
    if not proposal:
        print("Please provide a proposal to review.", file=sys.stderr)
        return 1

    try:
        feedback = review_proposal(proposal)
    except genai.errors.APIError as error:
        print(_api_error_message(error), file=sys.stderr)
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
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    print(f"\nStrength: {feedback['strength']}")
    print(f"\nWeakness: {feedback['weakness']}")
    print(f"\nRewritten opening sentence: {feedback['rewritten_opening_sentence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
