import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from google.genai import types


AGENT_PATH = Path(__file__).with_name("agent-tool.py")
SPEC = importlib.util.spec_from_file_location("kericho_agent", AGENT_PATH)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class FakeModels:
    def __init__(self, question: str) -> None:
        self.question = question
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append((model, contents, config))
        if len(self.calls) == 1 and self.question == "Is today good for harvesting?":
            content = types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            name="get_kericho_weather",
                            args={},
                        )
                    )
                ],
            )
            return types.GenerateContentResponse(
                candidates=[types.Candidate(content=content)]
            )

        answer = (
            "Rain is expected, so postpone harvesting and check again later."
            if len(self.calls) > 1
            else "Tea harvesting involves plucking suitable young leaves."
        )
        content = types.Content(
            role="model",
            parts=[types.Part(text=answer)],
        )
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=content)]
        )


class FakeClient:
    def __init__(self, question: str) -> None:
        self.models = FakeModels(question)


def weather_api_response():
    times = [f"2026-06-01T{hour:02d}:00" for hour in range(8, 15)]
    return {
        "current": {
            "time": "2026-06-01T08:00",
            "temperature_2m": 22.0,
            "relative_humidity_2m": 55,
            "precipitation": 0.0,
            "rain": 0.0,
        },
        "hourly": {
            "time": times,
            "precipitation": [0.0, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0],
        },
    }


class KerichoAgentTests(unittest.TestCase):
    def test_harvest_question_calls_weather_tool_and_returns_recommendation(self):
        client = FakeClient("Is today good for harvesting?")
        http_response = Mock()
        http_response.json.return_value = weather_api_response()

        with patch("httpx.get", return_value=http_response) as weather_request:
            answer = agent.ask_agent(client, "Is today good for harvesting?")

        self.assertIn("postpone harvesting", answer)
        weather_request.assert_called_once()
        self.assertEqual(len(client.models.calls), 2)
        system_prompt = client.models.calls[0][2].system_instruction
        self.assertIn("no rain in the next 6 hours", system_prompt)
        self.assertIn("15°C through 25°C", system_prompt)
        self.assertIn("above 28°C", system_prompt)
        function_responses = client.models.calls[1][1][-1].parts
        self.assertEqual(
            function_responses[0].function_response.response[
                "rain_expected_next_6_hours"
            ],
            True,
        )

    def test_general_tea_question_does_not_call_weather(self):
        client = FakeClient("How should tea leaves be picked?")
        with patch("httpx.get") as weather_request:
            answer = agent.ask_agent(client, "How should tea leaves be picked?")

        self.assertIn("plucking", answer)
        weather_request.assert_not_called()
        self.assertEqual(len(client.models.calls), 1)

    def test_unrelated_question_does_not_call_weather(self):
        client = FakeClient("What is the capital of Kenya?")
        with patch("httpx.get") as weather_request:
            agent.ask_agent(client, "What is the capital of Kenya?")

        weather_request.assert_not_called()
        self.assertEqual(len(client.models.calls), 1)

    def test_weather_tool_parses_current_and_next_six_hour_rain(self):
        http_response = Mock()
        http_response.json.return_value = weather_api_response()
        with patch("httpx.get", return_value=http_response) as weather_request:
            weather = agent.get_kericho_weather()

        self.assertEqual(weather["temperature_c"], 22.0)
        self.assertEqual(weather["relative_humidity_percent"], 55.0)
        self.assertTrue(weather["rain_expected_next_6_hours"])
        self.assertEqual(len(weather["forecast_next_6_hours"]), 6)
        weather_request.assert_called_once()
        self.assertEqual(
            weather_request.call_args.kwargs["params"]["timezone"],
            "Africa/Nairobi",
        )


if __name__ == "__main__":
    unittest.main()
