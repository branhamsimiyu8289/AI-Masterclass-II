import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
SYSTEM_INSTRUCTION = """
You are an automated assistant helping a Matatu SACCO secretary in Thika, Kenya.
Answer member questions clearly, politely, and using only the sample information
below. These are demonstration values; do not make up other balances, dates,
fees, or member-specific account details.

Common questions and answers:
1. Member balance: The sample account balance is KSh 12,500, including mandatory
   shares and welfare contributions through the end of last month.
2. Next meeting: The next General Member Meeting is Saturday, October 31, 2026,
   at 10:00 AM at the Thika Main Stage Office Hall. Attendance is mandatory for
   active route operators.
3. Membership fees: Registration for new members is KSh 5,000. The monthly
   welfare subscription is KSh 1,500, due by the 5th of each month.

Recognize variations in wording, including informal phrasing. If a question is
not about balances, meetings, or fees, politely explain that you can only help
with those topics and direct the member to the secretary.
"""

DEMO_QUESTIONS = (
    "How much money do I have in my account right now?",
    "Kindly check my balance for me please.",
    "Niaje, when is our next SACCO meeting happening?",
    "Is there a meeting this weekend?",
    "What are the charges to join or remain a member?",
    "How much is the monthly welfare contribution?",
)


def answer_member_query(client: genai.Client, user_question: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=user_question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        ),
    )
    return response.text or "The assistant did not return a text response."


def main() -> int:
    load_dotenv(Path(__file__).with_name(".env"))

    parser = argparse.ArgumentParser(
        description="Answer Matatu SACCO member questions with Gemini."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run six sample questions to demonstrate common query variations",
    )
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Add it to the .env file or your environment.",
            file=sys.stderr,
        )
        return 1

    print("=======AI SECRETARY ASSISTANT=======")
    print(
        "Welcome to the Matatu SACCO Secretary Assistant. Ask a question about "
        "your account balance, the next meeting, or membership fees."
    )

    questions = DEMO_QUESTIONS if args.demo else (input("Member question: ").strip(),)
    if not args.demo and not questions[0]:
        print("Please enter a question.", file=sys.stderr)
        return 1

    client = genai.Client(api_key=api_key)
    for index, question in enumerate(questions, start=1):
        if args.demo:
            print(f"\nTest {index} | Member asked: {question}")

        try:
            answer = answer_member_query(client, question)
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

        print(f"Assistant: {answer}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
