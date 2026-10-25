import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
ENV_FILE = APP_DIR.parent / "rest-country-api" / ".env"
API_URL = "https://api.restcountries.com/countries/v5/names.common/"


def load_api_key():
    api_key = os.environ.get("RESTCOUNTRIES_API_KEY")
    if api_key:
        return api_key

    try:
        env_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(
            f"Could not read the API key file at {ENV_FILE}."
        ) from error

    for line in env_lines:
        match = re.match(
            r"^\s*(?:export\s+)?RESTCOUNTRIES_API_KEY\s*=\s*(.*?)\s*$",
            line,
        )
        if match:
            api_key = match.group(1)
            if len(api_key) >= 2 and api_key[0] == api_key[-1] and api_key[0] in "\"'":
                api_key = api_key[1:-1]
            if api_key:
                return api_key

    raise RuntimeError(f"RESTCOUNTRIES_API_KEY was not found in {ENV_FILE}.")


API_KEY = load_api_key()


class CountryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def do_GET(self):
        parsed_url = urlsplit(self.path)
        if parsed_url.path == "/api/country":
            self.handle_country_request(parsed_url.query)
            return

        if parsed_url.path == "/":
            self.path = "/day4_fetch.html"
        super().do_GET()

    def handle_country_request(self, query):
        country = parse_qs(query).get("name", [""])[0].strip()
        if not country:
            self.send_json(400, {"errors": [{"message": "Enter a country name."}]})
            return

        request = Request(
            API_URL + quote(country, safe=""),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "User-Agent": "BrowserCountryLookup/1.0",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
                self.send_json(response.status, payload)
        except HTTPError as error:
            self.send_json(
                error.code,
                {"errors": [{"message": f"Country API returned HTTP {error.code}."}]},
            )
        except (URLError, TimeoutError, OSError):
            self.send_json(
                502,
                {"errors": [{"message": "Could not connect to the country API."}]},
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(
                502,
                {"errors": [{"message": "The country API returned invalid data."}]},
            )

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), CountryHandler)
    print("Open http://127.0.0.1:8000/ in your browser. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
