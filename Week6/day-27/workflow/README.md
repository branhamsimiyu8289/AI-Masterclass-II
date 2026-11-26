# Topic Research & Professional Brief Workflow (Gemini API)

A Python CLI workflow (`workflow.py`) that takes any topic, plans targeted research queries, gathers reference sources, summarizes the findings with the Google Gemini API, and formats the result as a professional Markdown brief.

## What Was Built

- **4-Stage Gemini AI Pipeline (`workflow.py`)**:
  1. **Research Planning (`plan_research`)**: Uses Gemini structured JSON output to define the research objective, 3 targeted search queries, and 4 analytical focus areas.
  2. **Source Gathering & Research (`research_topic`)**: Queries the public Wikipedia API (`search_wikipedia`) for factual background extracts and source URLs, optionally pairs with Gemini Google Search grounding (with automatic fallback to standard Gemini generation if grounding is unavailable), and compiles structured research notes.
  3. **AI Summarization (`summarize_findings`)**: Distills raw notes and references into core insights, key drivers, risks/gaps, and practical implications.
  4. **Professional Brief Formatting (`format_professional_brief`)**: Formats the synthesis into a ready-to-share Markdown brief (`Executive Summary`, `Background & Context`, `Key Findings`, `Risks, Constraints & Open Questions`, `Strategic Recommendations`, and `Sources & References`).
- **Resilient Gemini REST Client (`httpx`)**: Calls the Gemini `generateContent` endpoint using `x-goog-api-key` authentication, filters out thinking tokens, and automatically falls back across `gemini-flash-lite-latest`, `gemini-flash-latest`, `gemini-3.1-flash-lite-preview`, and `gemini-3-flash-preview`.
- **Flexible CLI & File Export**: Supports interactive prompts or CLI arguments for `--audience`, `--tone`, `--model`, `--output`, `--save`, and `--no-web`.

## Requirements

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- Packages in `requirements.txt` (`httpx`, `python-dotenv`)

## Setup

1. Install dependencies (if not already installed):

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Create a `.env` file from `.env.example` and add your Gemini API key:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edit `.env`:

   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## How to Run

From `Week6\day-27\workflow`:

- **Interactive mode (prompts for a topic):**

  ```powershell
  python workflow.py
  ```

- **Direct topic mode:**

  ```powershell
  python workflow.py "East Africa solar microgrid financing"
  ```

- **Customize audience, tone, and save to a Markdown file:**

  ```powershell
  python workflow.py "AI regulation in healthcare" --audience "Hospital Executives" --tone executive -o brief.md
  ```

- **Auto-save to `briefs/<topic-slug>.md`:**

  ```powershell
  python workflow.py "Cold-chain logistics for Kenyan agriculture" --save
  ```

- **Skip external web/Wikipedia lookup (pure Gemini synthesis):**

  ```powershell
  python workflow.py "Zero-trust network architecture" --no-web
  ```

## Run Unit Tests

```powershell
python -B -m unittest -v test_workflow.py
```
