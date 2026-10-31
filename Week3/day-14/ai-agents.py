import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
MAX_TOOL_ROUNDS = 5

inventory = {
    "maize flour": 120,
    "wheat flour": 85,
    "rice": 200,
    "sugar": 0,
    "cooking oil": 45,
}

prices = {
    "maize flour": 2800,
    "wheat flour": 3200,
    "rice": 4500,
}


def get_stock_level(product_name: str) -> str:
    display_name = product_name.strip()
    product = display_name.casefold()
    if product not in inventory:
        return f"Product '{display_name}' not found in the system."
    quantity = inventory[product]
    if quantity == 0:
        return f"{display_name} is currently out of stock."
    return f"{display_name}: {quantity} bags in stock."


def get_price(product_name: str) -> str:
    display_name = product_name.strip()
    product = display_name.casefold()
    if product not in prices:
        return f"Price not found for '{display_name}'."
    return f"{display_name}: KES {prices[product]:,} per bag."


def _function_declaration(name: str, description: str) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "product_name": types.Schema(
                    type=types.Type.STRING,
                    description="The product name, such as maize flour or rice.",
                )
            },
            required=["product_name"],
        ),
    )


TOOLS = [
    types.Tool(
        function_declarations=[
            _function_declaration(
                "get_stock_level",
                "Get the current stock quantity for a product at Kamau Stores.",
            ),
            _function_declaration(
                "get_price",
                "Get the current price per bag for a product at Kamau Stores.",
            ),
        ]
    )
]


def _run_tool(name: str | None, arguments: dict[str, object] | None) -> str:
    tool = {
        "get_stock_level": get_stock_level,
        "get_price": get_price,
    }.get(name or "")
    if tool is None:
        return f"Unknown tool: {name}"

    product_name = (arguments or {}).get("product_name")
    if not isinstance(product_name, str) or not product_name.strip():
        return "Invalid tool arguments: product_name must be a non-empty string."
    return tool(product_name)


def ask_agent(client: genai.Client, question: str) -> str:
    contents: list[types.Content | str] = [question]
    config = types.GenerateContentConfig(tools=TOOLS)

    for tool_round in range(MAX_TOOL_ROUNDS + 1):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )
        candidates = response.candidates or []
        if not candidates or candidates[0].content is None:
            raise RuntimeError("Gemini returned no response content.")

        model_content = candidates[0].content
        function_calls = [
            part.function_call
            for part in model_content.parts or []
            if part.function_call is not None
        ]
        if not function_calls:
            if not response.text:
                raise RuntimeError("Gemini returned no answer text.")
            return response.text

        if tool_round == MAX_TOOL_ROUNDS:
            raise RuntimeError(
                f"Gemini exceeded the limit of {MAX_TOOL_ROUNDS} tool-call rounds."
            )

        contents.append(model_content)
        function_responses = []
        for function_call in function_calls:
            if not function_call.name:
                raise RuntimeError("Gemini returned a tool call without a name.")
            print(f"Calling {function_call.name}...", flush=True)
            result = _run_tool(function_call.name, function_call.args)
            function_responses.append(
                types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": result},
                )
            )
        contents.append(types.Content(role="user", parts=function_responses))

    raise RuntimeError("Gemini did not finish the request.")


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Add it to Week3/.env or your environment.",
            file=sys.stderr,
        )
        return 1

    question = input("Ask Kamau Stores about stock or prices: ").strip()
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
        answer = ask_agent(client, question)
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
    except RuntimeError as error:
        print(f"Agent error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
