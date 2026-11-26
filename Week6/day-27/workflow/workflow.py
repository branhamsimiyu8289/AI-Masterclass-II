"""
Topic Research & Professional Brief Workflow (Gemini API)
---------------------------------------------------------
Multi-step AI workflow that takes a topic, plans research queries, gathers
background sources (Wikipedia + optional Gemini Google Search grounding),
synthesizes key findings with Google Gemini, and formats the output as a
professional Markdown brief.

Usage:
    python workflow.py
    python workflow.py "East Africa solar microgrid financing"
    python workflow.py "AI regulation in healthcare" --audience "Hospital Executives" -o brief.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import httpx
from dotenv import find_dotenv, load_dotenv

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 45.0
WIKIPEDIA_TIMEOUT_SECONDS = 12.0
USER_AGENT = "AI-Masterclass-ResearchWorkflow/1.0 (educational-cli)"


class GeminiAuthError(RuntimeError):
    """Raised when the Gemini API rejects authentication (HTTP 401/403)."""


@dataclass
class SourceItem:
    """Represents a single reference source retrieved during research."""

    title: str
    url: str
    snippet: str
    origin: str = "wikipedia"


@dataclass
class ResearchPlan:
    """Structured research plan generated for a topic."""

    topic: str
    objective: str
    queries: list[str]
    focus_areas: list[str]


@dataclass
class ResearchFindings:
    """Aggregated raw sources and synthesized research summary."""

    plan: ResearchPlan
    sources: list[SourceItem] = field(default_factory=list)
    ai_research_notes: str = ""
    synthesized_summary: str = ""
    models_used: list[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Complete output of the research-to-brief workflow."""

    topic: str
    audience: str
    tone: str
    findings: ResearchFindings
    brief_markdown: str
    output_path: Path | None = None


def load_api_key() -> str:
    """Load GEMINI_API_KEY from a nearby .env file or environment variable."""
    script_env = Path(__file__).resolve().parent / ".env"
    if script_env.is_file():
        load_dotenv(script_env, override=False)

    found_env = find_dotenv(usecwd=True)
    if found_env:
        load_dotenv(found_env, override=False)

    return os.getenv("GEMINI_API_KEY", "").strip()


def resolve_models(model_override: str | None = None) -> list[str]:
    """Return ordered Gemini model candidates, putting any explicit override first."""
    env_model = os.getenv("GEMINI_MODEL", "").strip()
    preferred = (model_override or env_model).strip()
    if not preferred:
        return list(DEFAULT_MODELS)
    return [preferred] + [m for m in DEFAULT_MODELS if m != preferred]


def _extract_response_text(data: dict[str, Any]) -> str:
    """Extract non-thought text parts from a Gemini generateContent JSON payload."""
    candidates = data.get("candidates", [])
    if not candidates or "content" not in candidates[0]:
        return ""
    parts = candidates[0]["content"].get("parts", [])
    text_parts = [
        p.get("text", "")
        for p in parts
        if p.get("text") and not p.get("thought")
    ]
    return "\n".join(text_parts).strip()


def _extract_grounding_sources(data: dict[str, Any]) -> list[SourceItem]:
    """Extract grounding web chunks when Gemini Search Grounding returns metadata."""
    candidates = data.get("candidates", [])
    if not candidates:
        return []
    metadata = candidates[0].get("groundingMetadata") or {}
    chunks = metadata.get("groundingChunks") or []
    sources: list[SourceItem] = []
    seen_urls: set[str] = set()
    for chunk in chunks:
        web = chunk.get("web") or {}
        url = (web.get("uri") or "").strip()
        title = (web.get("title") or url or "Web Source").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append(
                SourceItem(
                    title=title,
                    url=url,
                    snippet="Referenced via Gemini Google Search grounding.",
                    origin="google_search",
                )
            )
    return sources


def call_gemini(
    prompt: str,
    api_key: str,
    *,
    system_instruction: str = "",
    models: Sequence[str] | None = None,
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
    response_mime_type: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    http_client: httpx.Client | None = None,
) -> tuple[str, str, list[SourceItem]]:
    """
    Call the Gemini generateContent REST API with model fallback.

    Returns (response_text, model_used, grounding_sources).
    """
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. Set it in a .env file or environment variable."
        )

    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        raise ValueError("Prompt cannot be empty.")

    model_candidates = list(models) if models else list(DEFAULT_MODELS)
    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": cleaned_prompt}]}],
        "generationConfig": generation_config,
    }
    if system_instruction.strip():
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction.strip()}]
        }
    if tools:
        payload["tools"] = tools

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
    last_error = "Unknown error"

    try:
        for model_name in model_candidates:
            url = f"{GEMINI_API_BASE}/{model_name}:generateContent"
            try:
                response = client.post(
                    url,
                    headers={"x-goog-api-key": api_key},
                    json=payload,
                )
            except httpx.TimeoutException:
                last_error = f"Request timed out after {int(REQUEST_TIMEOUT_SECONDS)}s ({model_name})"
                continue
            except httpx.RequestError as exc:
                last_error = f"Network error ({model_name}): {exc}"
                continue

            if response.status_code == 200:
                data = response.json()
                answer = _extract_response_text(data)
                if answer:
                    grounding_sources = _extract_grounding_sources(data)
                    return answer, model_name, grounding_sources
                last_error = f"Gemini returned an empty response ({model_name})."
                continue

            if response.status_code in (401, 403):
                raise GeminiAuthError(
                    "Gemini API authentication failed. Check that GEMINI_API_KEY is valid."
                )

            try:
                err_msg = (
                    response.json()
                    .get("error", {})
                    .get("message", response.text[:200])
                )
            except Exception:
                err_msg = response.text[:200]
            last_error = f"HTTP {response.status_code} ({model_name}): {err_msg}"
    finally:
        if owns_client:
            client.close()

    raise RuntimeError(f"Could not get a response from Gemini API: {last_error}")


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object from model output, stripping optional Markdown fences."""
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return parsed


def plan_research(
    topic: str,
    api_key: str,
    *,
    audience: str = "Decision Makers & Stakeholders",
    models: Sequence[str] | None = None,
    http_client: httpx.Client | None = None,
) -> tuple[ResearchPlan, str]:
    """Stage 1: Ask Gemini to break the topic into targeted search queries and focus areas."""
    system_instruction = (
        "You are a senior research strategist. Return concise, practical research plans "
        "as valid JSON only."
    )
    prompt = f"""Create a focused research plan for the following topic.

Topic: {topic}
Target Audience: {audience}

Return a JSON object with exactly these keys:
- "objective": string (1-2 sentences describing what the brief should clarify)
- "queries": array of 3 short search queries (2-5 words each, suitable for encyclopedia/web search)
- "focus_areas": array of 4 key analytical angles to investigate"""

    raw_text, model_used, _ = call_gemini(
        prompt,
        api_key,
        system_instruction=system_instruction,
        models=models,
        temperature=0.2,
        max_output_tokens=768,
        response_mime_type="application/json",
        http_client=http_client,
    )

    try:
        data = _parse_json_object(raw_text)
        objective = str(data.get("objective") or "").strip() or (
            f"Investigate key facts, trends, risks, and recommendations for {topic}."
        )
        queries = [
            str(q).strip()
            for q in (data.get("queries") or [])
            if str(q).strip()
        ][:4]
        focus_areas = [
            str(a).strip()
            for a in (data.get("focus_areas") or [])
            if str(a).strip()
        ][:5]
    except (ValueError, json.JSONDecodeError):
        objective = f"Investigate key facts, trends, risks, and recommendations for {topic}."
        queries = [topic]
        focus_areas = [
            "Core definitions and background",
            "Current trends and drivers",
            "Challenges and risks",
            "Actionable recommendations",
        ]

    if not queries:
        queries = [topic]
    if not focus_areas:
        focus_areas = [
            "Background and context",
            "Key developments",
            "Risks and trade-offs",
            "Strategic recommendations",
        ]

    return (
        ResearchPlan(
            topic=topic,
            objective=objective,
            queries=queries,
            focus_areas=focus_areas,
        ),
        model_used,
    )


def search_wikipedia(
    queries: Sequence[str],
    *,
    max_sources: int = 5,
    http_client: httpx.Client | None = None,
) -> list[SourceItem]:
    """Retrieve factual background summaries from the public Wikipedia API."""
    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=WIKIPEDIA_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )

    sources: list[SourceItem] = []
    seen_titles: set[str] = set()

    try:
        for query in queries:
            if len(sources) >= max_sources:
                break
            cleaned_query = query.strip()
            if not cleaned_query:
                continue

            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": cleaned_query,
                "gsrlimit": 2,
                "prop": "extracts|info",
                "exintro": 1,
                "explaintext": 1,
                "exchars": 700,
                "inprop": "url",
                "format": "json",
            }
            try:
                resp = client.get(
                    WIKIPEDIA_API_URL,
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=WIKIPEDIA_TIMEOUT_SECONDS,
                )
                if resp.status_code != 200:
                    continue
                payload = resp.json()
            except (httpx.HTTPError, ValueError):
                continue

            pages = (payload.get("query") or {}).get("pages") or {}
            ordered_pages = sorted(
                pages.values(),
                key=lambda item: item.get("index", 999),
            )
            for page in ordered_pages:
                if len(sources) >= max_sources:
                    break
                title = (page.get("title") or "").strip()
                extract = re.sub(r"\s+", " ", (page.get("extract") or "")).strip()
                url = (page.get("fullurl") or "").strip()
                if not title or not extract or title in seen_titles:
                    continue
                seen_titles.add(title)
                if not url:
                    slug = title.replace(" ", "_")
                    url = f"https://en.wikipedia.org/wiki/{slug}"
                sources.append(
                    SourceItem(
                        title=title,
                        url=url,
                        snippet=extract,
                        origin="wikipedia",
                    )
                )
    finally:
        if owns_client:
            client.close()

    return sources


def research_topic(
    plan: ResearchPlan,
    api_key: str,
    *,
    use_web: bool = True,
    models: Sequence[str] | None = None,
    http_client: httpx.Client | None = None,
) -> tuple[list[SourceItem], str, str]:
    """
    Stage 2: Gather external sources (Wikipedia + optional Gemini Search Grounding)
    and compile structured AI research notes.
    """
    sources: list[SourceItem] = []
    if use_web:
        search_queries = [plan.topic] + [
            q for q in plan.queries if q.lower() != plan.topic.lower()
        ]
        sources.extend(search_wikipedia(search_queries, http_client=http_client))

    source_context = (
        "\n\n".join(
            f"- [{idx}] {src.title} ({src.url})\n  {src.snippet}"
            for idx, src in enumerate(sources, start=1)
        )
        if sources
        else "No external encyclopedia snippets retrieved."
    )

    research_prompt = f"""Conduct structured research on the topic below using the provided reference snippets and your domain knowledge.

Topic: {plan.topic}
Objective: {plan.objective}
Focus Areas:
{chr(10).join(f"- {area}" for area in plan.focus_areas)}

Retrieved Reference Snippets:
{source_context}

Provide organized research notes covering each focus area. Clearly distinguish facts supported by retrieved references from broader industry/domain context, and flag any areas where data may vary by region or timeframe."""

    system_instruction = (
        "You are a thorough research analyst. Be accurate, balanced, and explicit "
        "about evidence, trade-offs, and uncertainty. Never invent citations or fake URLs."
    )

    grounding_sources: list[SourceItem] = []
    if use_web:
        try:
            notes, model_used, grounding_sources = call_gemini(
                research_prompt,
                api_key,
                system_instruction=system_instruction,
                models=models,
                temperature=0.3,
                max_output_tokens=2048,
                tools=[{"google_search": {}}],
                http_client=http_client,
            )
        except GeminiAuthError:
            raise
        except RuntimeError:
            # Fall back to standard Gemini generation if search grounding is unavailable
            notes, model_used, _ = call_gemini(
                research_prompt,
                api_key,
                system_instruction=system_instruction,
                models=models,
                temperature=0.3,
                max_output_tokens=2048,
                http_client=http_client,
            )
    else:
        notes, model_used, _ = call_gemini(
            research_prompt,
            api_key,
            system_instruction=system_instruction,
            models=models,
            temperature=0.3,
            max_output_tokens=2048,
            http_client=http_client,
        )

    existing_urls = {s.url for s in sources}
    for src in grounding_sources:
        if src.url not in existing_urls:
            sources.append(src)
            existing_urls.add(src.url)

    return sources, notes, model_used


def summarize_findings(
    plan: ResearchPlan,
    sources: Sequence[SourceItem],
    research_notes: str,
    api_key: str,
    *,
    models: Sequence[str] | None = None,
    http_client: httpx.Client | None = None,
) -> tuple[str, str]:
    """Stage 3: Synthesize raw research notes into distilled key takeaways."""
    system_instruction = (
        "You are an executive intelligence analyst. Distill complex research into "
        "clear, high-signal, non-repetitive findings."
    )
    prompt = f"""Synthesize the research notes below into a concise analytical summary.

Topic: {plan.topic}
Objective: {plan.objective}
Sources Count: {len(sources)}

Research Notes:
{research_notes}

Organize your synthesis into:
1. Core Insights (4-6 crisp bullet points)
2. Key Drivers & Mechanisms
3. Primary Risks, Limitations, or Knowledge Gaps
4. Practical Implications"""

    summary, model_used, _ = call_gemini(
        prompt,
        api_key,
        system_instruction=system_instruction,
        models=models,
        temperature=0.2,
        max_output_tokens=1536,
        http_client=http_client,
    )
    return summary, model_used


def format_professional_brief(
    findings: ResearchFindings,
    api_key: str,
    *,
    audience: str = "Decision Makers & Stakeholders",
    tone: str = "executive",
    models: Sequence[str] | None = None,
    http_client: httpx.Client | None = None,
) -> tuple[str, str]:
    """Stage 4: Format synthesized findings into a polished professional Markdown brief."""
    sources_block = (
        "\n".join(
            f"- [{src.title}]({src.url}) ({src.origin})"
            for src in findings.sources
        )
        if findings.sources
        else "- No external web URLs retrieved; brief synthesized from Gemini AI analysis."
    )

    system_instruction = (
        "You are a principal strategy advisor writing polished professional briefs. "
        "Use crisp headings, scannable bullet points, concrete takeaways, and an objective tone. "
        "Only cite URLs explicitly provided in the Sources list."
    )
    prompt = f"""Format the synthesized research below into a polished, publication-ready professional brief in Markdown.

Topic: {findings.plan.topic}
Target Audience: {audience}
Tone: {tone}
Date: {date.today().isoformat()}

Research Objective:
{findings.plan.objective}

Synthesized Findings:
{findings.synthesized_summary}

Verified Sources Retrieved:
{sources_block}

Required Markdown Structure:
# Brief: {findings.plan.topic}
**Prepared For:** {audience} | **Date:** {date.today().isoformat()} | **Tone:** {tone.title()}

## Executive Summary
(2-4 concise sentences summarizing the headline takeaway)

## Background & Context
(Brief framing of why this topic matters)

## Key Findings
(4-6 sharp, scannable bullet points with bold lead-ins)

## Risks, Constraints & Open Questions
(3-4 bullet points highlighting trade-offs, blind spots, or uncertainties)

## Strategic Recommendations
(3-5 actionable next steps tailored to {audience})

## Sources & References
(List only the verified sources provided above, or note if none were retrieved)"""

    brief_text, model_used, _ = call_gemini(
        prompt,
        api_key,
        system_instruction=system_instruction,
        models=models,
        temperature=0.25,
        max_output_tokens=2048,
        http_client=http_client,
    )
    return brief_text, model_used


def run_workflow(
    topic: str,
    api_key: str,
    *,
    audience: str = "Decision Makers & Stakeholders",
    tone: str = "executive",
    use_web: bool = True,
    models: Sequence[str] | None = None,
    output_path: Path | None = None,
    http_client: httpx.Client | None = None,
    progress_callback: Any | None = None,
) -> WorkflowResult:
    """Execute the full 4-stage research -> summarize -> professional brief pipeline."""
    cleaned_topic = topic.strip()
    if not cleaned_topic:
        raise ValueError("Topic cannot be empty.")

    def notify(step: str) -> None:
        if progress_callback:
            progress_callback(step)

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    try:
        notify("1/4 Planning research angles with Gemini...")
        plan, plan_model = plan_research(
            cleaned_topic,
            api_key,
            audience=audience,
            models=models,
            http_client=client,
        )

        notify("2/4 Researching topic and gathering sources...")
        sources, research_notes, research_model = research_topic(
            plan,
            api_key,
            use_web=use_web,
            models=models,
            http_client=client,
        )

        notify("3/4 Summarizing and synthesizing findings with Gemini...")
        summary, summary_model = summarize_findings(
            plan,
            sources,
            research_notes,
            api_key,
            models=models,
            http_client=client,
        )

        models_used = []
        for m in (plan_model, research_model, summary_model):
            if m and m not in models_used:
                models_used.append(m)

        findings = ResearchFindings(
            plan=plan,
            sources=sources,
            ai_research_notes=research_notes,
            synthesized_summary=summary,
            models_used=models_used,
        )

        notify("4/4 Formatting professional brief...")
        brief_md, brief_model = format_professional_brief(
            findings,
            api_key,
            audience=audience,
            tone=tone,
            models=models,
            http_client=client,
        )
        if brief_model and brief_model not in findings.models_used:
            findings.models_used.append(brief_model)

        saved_path: Path | None = None
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(brief_md + "\n", encoding="utf-8")
            saved_path = output_path

        return WorkflowResult(
            topic=cleaned_topic,
            audience=audience,
            tone=tone,
            findings=findings,
            brief_markdown=brief_md,
            output_path=saved_path,
        )
    finally:
        if owns_client:
            client.close()


def slugify_topic(topic: str) -> str:
    """Create a filesystem-safe filename slug from a topic string."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60] or "research-brief"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Research a topic, summarize findings with Gemini AI, and generate a professional brief."
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="Topic to research (if omitted, you will be prompted interactively).",
    )
    parser.add_argument(
        "-a",
        "--audience",
        default="Decision Makers & Stakeholders",
        help="Target audience for the brief (default: Decision Makers & Stakeholders).",
    )
    parser.add_argument(
        "--tone",
        default="executive",
        choices=["executive", "analytical", "technical", "policy"],
        help="Writing tone for the formatted brief (default: executive).",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Optional Gemini model name override (defaults to GEMINI_MODEL or built-in list).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output Markdown file path (e.g., brief.md).",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Automatically save the brief to briefs/<topic-slug>.md.",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Skip Wikipedia/web lookup and run pure Gemini research synthesis.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)
    api_key = load_api_key()
    if not api_key:
        print(
            "Error: GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.",
            file=sys.stderr,
        )
        return 1

    topic = (args.topic or "").strip()
    if not topic:
        try:
            topic = input("Enter the topic to research: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 1

    if not topic:
        print("Error: Topic cannot be empty.", file=sys.stderr)
        return 1

    output_path: Path | None = None
    if args.output:
        output_path = Path(args.output).expanduser()
    elif args.save:
        output_path = Path("briefs") / f"{slugify_topic(topic)}.md"

    models = resolve_models(args.model)
    print(f"Starting research workflow for: {topic}")

    try:
        result = run_workflow(
            topic,
            api_key,
            audience=args.audience,
            tone=args.tone,
            use_web=not args.no_web,
            models=models,
            output_path=output_path,
            progress_callback=lambda msg: print(f"  -> {msg}"),
        )
    except Exception as exc:
        print(f"Workflow failed: {exc}", file=sys.stderr)
        return 1

    print("\n" + "=" * 72 + "\n")
    print(result.brief_markdown)
    print("\n" + "=" * 72)
    print(
        f"Models used: {', '.join(result.findings.models_used)} | "
        f"Sources collected: {len(result.findings.sources)}"
    )
    if result.output_path is not None:
        print(f"Brief saved to: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
