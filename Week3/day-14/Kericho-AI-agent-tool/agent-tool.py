import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-3.5-flash-lite"
MAX_TOOL_ROUNDS = 5
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_LATITUDE = -0.3676
DEFAULT_LONGITUDE = 35.2830

SYSTEM_PROMPT = """\
You are a practical field assistant for a tea estate in Kericho, Kenya.
For any question about current weather, field conditions, or whether/when to
harvest, call get_kericho_weather before giving advice. Do not guess current
weather. For unrelated questions, answer normally without calling the weather
tool.

Use the returned current conditions and hourly precipitation forecast to give a
concise, practical recommendation in plain language. Apply these rules:
- Good harvesting conditions require no rain in the next 6 hours, a
  temperature from 15°C through 25°C, and low humidity (below 60%).
- Bad conditions include active rain or a temperature above 28°C; recommend
  postponing harvesting in these conditions.
- If conditions do not meet the good or bad rules, describe them as mixed and
  explain what the supervisor should monitor.
- If rain is forecast in the next 6 hours, do not call the conditions good.
- State the observed temperature, humidity, and rain outlook when relevant.
- If the weather tool reports an error, say that current conditions could not
  be checked; never invent weather data or a recommendation based on it.
"""

WEATHER_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_kericho_weather",
            description=(
                "Fetch current weather and hourly rainfall for the tea estate "
                "in Kericho, Kenya. Use for harvesting, weather, or field "
                "condition questions."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        )
    ]
)


def _estate_coordinates() -> tuple[float, float]:
    try:
        latitude = float(os.getenv("ESTATE_LATITUDE", str(DEFAULT_LATITUDE)))
        longitude = float(os.getenv("ESTATE_LONGITUDE", str(DEFAULT_LONGITUDE)))
    except ValueError as error:
        raise RuntimeError(
            "ESTATE_LATITUDE and ESTATE_LONGITUDE must be valid numbers."
        ) from error

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise RuntimeError(
            "Estate coordinates are outside valid latitude/longitude ranges."
        )
    return latitude, longitude


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"The weather service returned an invalid {field} value.")
    return float(value)


def get_kericho_weather() -> dict[str, object]:
    latitude, longitude = _estate_coordinates()
    response = httpx.get(
        OPEN_METEO_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,rain"
            ),
            "hourly": "precipitation",
            "forecast_days": 2,
            "timezone": "Africa/Nairobi",
        },
        timeout=15,
    )
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError("The weather service returned invalid JSON.") from error
    if not isinstance(data, dict):
        raise RuntimeError("The weather service returned an invalid response.")

    current = data.get("current")
    hourly = data.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise RuntimeError("The weather service response is missing forecast data.")

    current_time_value = current.get("time")
    times = hourly.get("time")
    precipitation = hourly.get("precipitation")
    if (
        not isinstance(current_time_value, str)
        or not isinstance(times, list)
        or not isinstance(precipitation, list)
        or len(times) != len(precipitation)
    ):
        raise RuntimeError("The weather service returned an invalid hourly forecast.")

    try:
        current_time = datetime.fromisoformat(current_time_value)
        six_hours_later = current_time + timedelta(hours=6)
        forecast = [
            {
                "time": hour,
                "precipitation_mm": _number(amount, "hourly precipitation"),
            }
            for hour, amount in zip(times, precipitation)
            if isinstance(hour, str)
            and current_time.replace(minute=0, second=0, microsecond=0)
            <= datetime.fromisoformat(hour)
            < six_hours_later
        ]
    except ValueError as error:
        raise RuntimeError("The weather service returned invalid forecast times.") from error

    if not forecast:
        raise RuntimeError("The weather service returned no forecast for the next 6 hours.")

    current_precipitation = _number(
        current.get("precipitation"), "current precipitation"
    )
    current_rain = _number(current.get("rain"), "current rain")
    temperature = _number(current.get("temperature_2m"), "temperature")
    humidity = _number(current.get("relative_humidity_2m"), "relative humidity")

    return {
        "location": "Kericho tea estate",
        "observed_at": current_time_value,
        "temperature_c": temperature,
        "relative_humidity_percent": humidity,
        "current_precipitation_mm": current_precipitation,
        "current_rain_mm": current_rain,
        "forecast_next_6_hours": forecast,
        "rain_expected_next_6_hours": any(
            hour["precipitation_mm"] > 0 for hour in forecast
        ),
    }


def _run_tool(name: str | None) -> dict[str, object]:
    if name != "get_kericho_weather":
        return {"error": f"Unknown tool: {name}"}
    return get_kericho_weather()


def ask_agent(client: genai.Client, question: str) -> str:
    contents: list[types.Content | str] = [question]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[WEATHER_TOOL],
    )

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
            result = _run_tool(function_call.name)
            function_responses.append(
                types.Part.from_function_response(
                    name=function_call.name,
                    response=result,
                )
            )
        contents.append(types.Content(role="user", parts=function_responses))

    raise RuntimeError("Gemini did not finish the request.")


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is missing. Add it to Week3/.env or your environment.",
            file=sys.stderr,
        )
        return 1

    question = input("Ask about Kericho weather or tea harvesting: ").strip()
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
        print("\nRecommendation:")
        print(answer)
    except genai.errors.APIError as error:
        message = error.message or "The service returned an error."
        print(f"Gemini API error ({error.code}): {message}", file=sys.stderr)
        return 1
    except httpx.TimeoutException:
        print(
            "A service did not respond within the timeout. Please try again.",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError as error:
        print(f"Could not fetch current weather: {error}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(f"Agent error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())