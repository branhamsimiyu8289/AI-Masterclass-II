# News API

A small FastAPI app that serves the Field Notes News page and fetches articles
from NewsAPI.

## Run locally (Windows PowerShell)

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Put your NewsAPI key in a `.env` file in this directory:

```text
NEWS_API_KEY=your_newsapi_key_here
```

Start the development server:

```powershell
python -m uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. The interactive API docs are at
<http://127.0.0.1:8000/docs>.

## Debug

- Keep the server terminal open; Python errors and request logs appear there.
- For breakpoints, open this folder in VS Code, create `.vscode/launch.json`
  with the configuration below, then set breakpoints in `main.py` and start
  **News API** from **Run and Debug**. `--reload` is intentionally omitted so
  the debugger stays attached to one process.

  ```json
  {
    "version": "0.2.0",
    "configurations": [
      {
        "name": "News API",
        "type": "debugpy",
        "request": "launch",
        "module": "uvicorn",
        "args": ["main:app", "--host", "127.0.0.1", "--port", "8000"]
      }
    ]
  }
  ```
- Check `/api/categories` first, then `/api/news?category=politics` to test the
  NewsAPI-backed endpoint. A missing key is reported as an API error.
- In browser developer tools, use **Network** and **Console** to inspect
  requests made by the page.

Keep `.env` private and do not commit or share your API key.
