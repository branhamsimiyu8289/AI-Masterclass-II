# Proposal Feedback Tool

Proposal Feedback Tool is a command-line app for freelancers who want a quick,
constructive review of a client proposal before submitting it. It sends your
proposal to Google's Gemini AI and prints:

- One specific strength
- One important, actionable weakness
- A clearer, more compelling rewrite of the opening sentence

The rewrite is instructed to stay truthful to the proposal and not invent
experience, skills, or promises. Review all AI suggestions and make sure they
accurately represent you before using them.

## Requirements

- Python 3.10 or later
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- An internet connection

## Install

Open a terminal in this `proposal-feedback-tool` folder.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install google-genai python-dotenv httpx
```

### macOS or Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install google-genai python-dotenv httpx
```

Create a file named `.env` in this folder and add your API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your own key. Keep it private. The `.gitignore`
in this folder excludes `.env`, so the key is not added to Git.

Alternatively, set `GEMINI_API_KEY` in your terminal environment.

## Use

### Paste a proposal interactively

Run the app with no proposal argument:

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\python.exe .\main.py
```

**macOS or Linux:**

```bash
.venv/bin/python main.py
```

Paste your proposal. When finished, enter `END` on a line by itself and press
Enter. The tool prints the strength, weakness, and rewritten opening sentence.

### Pass proposal text as an argument

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\python.exe .\main.py "I can build your booking website. I have experience with Python and React."
```

**macOS or Linux:**

```bash
.venv/bin/python main.py "I can build your booking website. I have experience with Python and React."
```

Use quotation marks around the proposal so it is passed as one piece of text.
For long proposals, the interactive method is more convenient.

To see command options, run `python main.py --help` (or use the virtual
environment's Python executable as shown above).

## Example interaction

```text
Paste your proposal below. Enter END on a line by itself when finished:
I can build your booking website. I have experience with Python and React.
END

Strength: You name relevant technologies and clearly identify the project.

Weakness: The proposal does not explain how your experience applies to this
client's booking website.

Rewritten opening sentence: I can build your booking website using my
experience with Python and React.
```

Gemini's wording will vary. The example is illustrative; the tool does not
verify that claims in a proposal are true.

## Privacy and errors

The proposal text is sent to Google's Gemini API for review. Do not include
confidential client details, passwords, or other sensitive information unless
you have confirmed the applicable Google API data-use terms.

The tool reports empty proposals without making an API request. It also
identifies rejected or unauthorized API keys, and reports Gemini API errors,
timeouts, connection problems, empty responses, and invalid or incomplete
feedback in the terminal.
