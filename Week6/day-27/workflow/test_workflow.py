import json
import tempfile
import unittest
from pathlib import Path

import httpx

import workflow


class WorkflowTests(unittest.TestCase):
    def test_resolve_models_puts_override_first(self) -> None:
        models = workflow.resolve_models("gemini-flash-latest")
        self.assertEqual(models[0], "gemini-flash-latest")
        self.assertEqual(len(models), len(set(models)))

    def test_slugify_topic_normalizes_text(self) -> None:
        self.assertEqual(
            workflow.slugify_topic("Kenya Solar Microgrids: 2026 Outlook!"),
            "kenya-solar-microgrids-2026-outlook",
        )

    def test_call_gemini_filters_thought_parts_and_falls_back_on_429(self) -> None:
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            self.assertEqual(request.headers.get("x-goog-api-key"), "test-key")
            if "gemini-flash-lite-latest" in request.url.path:
                return httpx.Response(
                    429,
                    json={"error": {"message": "Rate limit exceeded"}},
                )
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "Internal reasoning", "thought": True},
                                    {"text": "Final verified response."},
                                ]
                            },
                            "groundingMetadata": {
                                "groundingChunks": [
                                    {
                                        "web": {
                                            "uri": "https://example.org/report",
                                            "title": "Example Report",
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            text, model_used, sources = workflow.call_gemini(
                "Summarize solar trends",
                "test-key",
                http_client=client,
            )

        self.assertEqual(text, "Final verified response.")
        self.assertEqual(model_used, "gemini-flash-latest")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].url, "https://example.org/report")

    def test_call_gemini_fails_fast_on_auth_error(self) -> None:
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return httpx.Response(403, json={"error": {"message": "Forbidden"}})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(RuntimeError) as ctx:
                workflow.call_gemini("Test prompt", "bad-key", http_client=client)

        self.assertIn("authentication failed", str(ctx.exception).lower())
        self.assertEqual(len(calls), 1)

    def test_run_workflow_end_to_end_and_saves_brief(self) -> None:
        stages_seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "en.wikipedia.org":
                return httpx.Response(
                    200,
                    json={
                        "query": {
                            "pages": {
                                "10": {
                                    "index": 1,
                                    "title": "Microgrid",
                                    "fullurl": "https://en.wikipedia.org/wiki/Microgrid",
                                    "extract": "A microgrid is a localized group of electricity sources and loads.",
                                }
                            }
                        }
                    },
                )

            body = json.loads(request.content.decode("utf-8"))
            prompt_text = body["contents"][0]["parts"][0]["text"]

            if "Create a focused research plan" in prompt_text:
                stages_seen.append("plan")
                reply = json.dumps(
                    {
                        "objective": "Assess microgrid financing models.",
                        "queries": ["Microgrid", "Solar power in Kenya"],
                        "focus_areas": ["Capital costs", "Pay-as-you-go revenue"],
                    }
                )
            elif "Conduct structured research" in prompt_text:
                if "tools" in body:
                    return httpx.Response(
                        400,
                        json={"error": {"message": "Search grounding not enabled"}},
                    )
                stages_seen.append("research")
                reply = "Detailed research notes on solar microgrids."
            elif "Synthesize the research notes" in prompt_text:
                stages_seen.append("summarize")
                reply = "Synthesized key insights and risks."
            elif "Format the synthesized research" in prompt_text:
                stages_seen.append("format")
                reply = (
                    "# Brief: Solar Microgrid Financing\n\n"
                    "## Executive Summary\nBlended finance lowers unit costs."
                )
            else:
                raise AssertionError(f"Unexpected prompt: {prompt_text[:80]}")

            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": reply}]}}]},
            )

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "out" / "brief.md"
            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                result = workflow.run_workflow(
                    "Solar Microgrid Financing",
                    "test-key",
                    audience="Impact Investors",
                    tone="executive",
                    output_path=out_file,
                    http_client=client,
                )

            self.assertEqual(stages_seen, ["plan", "research", "summarize", "format"])
            self.assertTrue(out_file.is_file())
            saved_text = out_file.read_text(encoding="utf-8")
            self.assertIn("Executive Summary", saved_text)
            self.assertEqual(len(result.findings.sources), 1)
            self.assertEqual(result.findings.sources[0].title, "Microgrid")
            self.assertEqual(result.output_path, out_file)

    def test_main_requires_api_key(self) -> None:
        original = workflow.load_api_key
        workflow.load_api_key = lambda: ""
        try:
            code = workflow.main(["Solar Microgrids"])
        finally:
            workflow.load_api_key = original
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
