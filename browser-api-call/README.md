# Browser Country Lookup

This page uses the REST Countries v5 API. Since v5 requires an API key, run
the local Python server instead of opening `day4_fetch.html` directly. The
server reads `RESTCOUNTRIES_API_KEY` from `..\rest-country-api\.env`, sends
authenticated requests to v5, and keeps the key out of browser code.

From this directory, start the server:

```powershell
py server.py
```

Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The API key file
must contain a `RESTCOUNTRIES_API_KEY=...` entry and should remain private.
