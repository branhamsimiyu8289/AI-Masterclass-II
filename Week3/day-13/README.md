# Otieno Wholesale Chatbot

This project is a command-line Gemini chatbot for Otieno Wholesale in Kisumu.
I built it to answer customer questions about stock, pricing, and delivery in
KES, and to keep a record of each conversation instead of losing the exchange
when the session ends.

The chatbot keeps the latest 10 messages as Gemini conversation context and
saves the full session transcript to `chat_log.json` after you type `exit` (or
input ends). The log is created beside `chatbot.py` and is ignored by Git so
customer conversations are not accidentally committed. Since transcripts can
contain personal details, keep the local log private.

## Run

Set `GEMINI_API_KEY` in your environment or in the `Week3/.env` file. From the
`Week3` folder, install dependencies if needed:

```powershell
python -m pip install google-genai python-dotenv httpx
```

Start the chatbot:

```powershell
python .\day-13\chatbot.py
```

Type messages at the `You:` prompt. Type `exit` to end the conversation and
save the transcript.

## Sample output

```text
Otieno Wholesale Assistant. Type 'exit' to quit.

You: Where do you deliver?

Assistant: We deliver around Kisumu and its surrounding areas.

You: exit
Conversation saved to chat_log.json
```

See [example.txt](./example.txt) for the full sample conversation.
