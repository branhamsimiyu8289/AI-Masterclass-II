# AI Masterclass II: Automation and Automization

This repository contains projects, coding exercises, and planning materials
from **AI Masterclass II**, an AMERIX course. The projects explore how Python,
APIs, web applications, and AI assistants can support information lookup,
customer service, data entry, and other business workflows.

The repository is organized by course week and by standalone project. Each app
is an independent learning project with its own dependencies and run
instructions; there is no single command or dependency file for the entire
repository.

## Projects

### Standalone applications

| Project | Description |
|---|---|
| [browser-api-call/](./browser-api-call/) | Country Info browser app. Its HTML page searches the REST Countries v5 API through a local Python server, which keeps the API key out of browser code. Configure a key in the project's `.env`, start `server.py`, and open the local page; see the [project README](./browser-api-call/README.md). |
| [email-drafter/](./email-drafter/) | Gemini-powered command-line tool that drafts concise Kenyan business emails from a topic. See its README for setup, API-key configuration, and usage. |
| [news-api/](./news-api/) | FastAPI service and browser interface for browsing politics, weather, sports, and agriculture headlines from NewsAPI. |
| [rest-country-api/](./rest-country-api/) | Command-line country lookup for capitals, population, and currency using the REST Countries API; it requires an API key. |
| [travel-app/](./travel-app/) | Travel weather and location tool that accepts place names or GPS coordinates, adds a country profile, and exports a JSON report. |
| [weather-app/](./weather-app/) | Command-line settlement and weather lookup with local sunrise and sunset times, using OpenStreetMap Nominatim and OpenWeather. |

### Week 2: The Client Cycle

[`Week2/`](./Week2/) contains business workflow planning materials: an AI-agent
client brief and proposal, a dashboard handoff, and an attendance-SMS project
agreement.

The [dairy-price-checker](./Week2/dairy-price-checker/) is a FastAPI and SQLite
progressive web app for recording milk deliveries and calculating farmer
payments. It includes a farmer entry page, live price updates, and an admin
dashboard for managing prices and daily records.

### Week 3: Building With AI API

| Folder | Description |
|---|---|
| [Day 11: My First AI API Call](./Week3/day-11/) | Command-line question-and-answer program using Google's Gemini API. |
| [Day 12: Prompt Engineering For Developers](./Week3/day-12/) | Kamau Stores customer-service assistant and a property inquiry extractor that returns structured JSON. |
| [Day 13: Building a Chatbot](./Week3/day-13/) | Otieno Wholesale chatbot with bounded conversation context and a local transcript; includes a [Kisumu Pharmacy chatbot](./Week3/day-13/Kisumu-Pharmacy-Chatbot/) for staff support and contextual follow-up questions. |
| [Day 14: Function Calling And AI Agents](./Week3/day-14/) | Gemini tool-calling inventory and price assistant for Kamau Stores, plus the [Kericho tea harvesting agent](./Week3/day-14/Kericho-AI-agent-tool/) that checks weather and the six-hour rain forecast before recommending whether to harvest. |

### Week 4: Web Applications

The [Day 16: Flask Basics](./Week4/day-16/) project is a small Flask web app for looking up
sample customer credit balances at an Eldoret hardware shop. Search by customer
name in the browser or use the JSON API. It demonstrates a simple business
lookup workflow using an HTML form, a Flask endpoint, and hardcoded sample
balances. Its project README covers the problem, solution, features, setup, run
instructions, and example output.

The [Day 17: Building a REST API](./Week4/day-17/) folder contains two API projects. The Flask
[Orders API](./Week4/day-17/README.md) lists, creates, and looks up sample
orders and updates their statuses; orders are stored in memory. The nested
[today's_exercise app](./Week4/day-17/today's_exercise/) is a FastAPI poultry
egg-production manager with a farmer dashboard, SQLite persistence, shed and
date filtering, tray calculations, and weekly WhatsApp reconciliation. See its
[project README](./Week4/day-17/today's_exercise/README.md) for setup, API
endpoints, and tests.

The [Day 18: Connecting Frontend and Backend](./Week4/day-18/full-stack/) project is a Flask web app
for tracking daily egg production by shed. It provides a browser dashboard and
REST API for recording entries and viewing running totals. Records are stored
in SQLite, so they persist across app restarts when the database is on
persistent storage. To install its dependencies and start it from PowerShell
at the repository root:

```powershell
cd .\Week4\day-18\full-stack
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in a browser. Run the install command with the
same Python interpreter used to start the app; in VS Code, select that
interpreter if Flask cannot be imported. See the [project README](./Week4/day-18/full-stack/README.md)
for details and tests.

For Render deployment, create a Blueprint from this repository; the root
[render.yaml](./render.yaml) configures the app's subdirectory, Gunicorn start
command, health check, and persistent disk for the SQLite database. The
persistent disk requires a paid Render web-service plan. The optional
`DELETE /api/eggs` endpoint is disabled unless a `RESET_TOKEN` environment
variable is configured.

The [Day 19: Deploying My Application](./Week4/day-19/README.md) README presents the Kiambu Poultry Farm
egg tracker, including its [live demo](https://egg-production-tracker-v8w1.onrender.com/),
feature overview, setup and testing instructions, Render deployment notes, and
Kenyan SME market and pricing analysis.

The [Day 20: Deployed AI Web Application](./Week4/day-20/) is a focused web tool built for small Nairobi
businesses (courier services, shops, Airbnbs, and restaurants) receiving customer
complaints on WhatsApp. Powered by Google Gemini AI (with a resilient local SME
engine fallback), it provides an ultra-minimal interface (one text box, one button)
that instantly drafts polite, blame-free, reassuring replies with clear next steps.
Try the [live demo](https://nairobi-complaint-reply-tool.onrender.com/) or see its
[project README](./Week4/day-20/README.md) for features, setup, and commercial
client pricing strategy.

### Week 5: Automation and Productivity Tools

The [Day 21: File Automation CLI](./Week5/day-21/file-automation/app.py) demonstrates
safe, preview-first file tasks, including organizing files, spreadsheet backups,
and photo renaming. Run `python app.py --help` from its folder to see the commands.

The [Day 21 law-firm sorter](./Week5/day-21/law-firm-sorter/README.md) groups
documents by file extension, previews moves before applying them, and records
completed moves in an audit log. Its README explains local-folder usage and setup.

The [Day 22: Web Scraping Basics](./Week5/day-22/web-scraper/README.md) project scrapes book titles,
prices, and ratings from Books to Scrape using requests and BeautifulSoup, featuring
retries with backoff and CSV export.

The [Day 22 job-market-tracker](./Week5/day-22/job-market-tracker/README.md) is a
safe prototype using `quotes.toscrape.com` to map quote text, authors, and tags to
example HR market-intelligence fields. Its README covers adapting the approach for
an authorized jobs board, KDPA considerations, and a weekly client pricing model.

The [Day 23: Email and Notification Automation](./Week5/day-23/email-automation/)
includes SMTP email examples and a [retail sales reporter](./Week5/day-23/retail-sales-reporter/README.md)
that reads point-of-sale CSV data, calculates daily sales metrics, flags low
stock, and can send an HTML report by email or generate a local preview. See its
README for dependency installation, `.env` setup, dry-run, scheduling, and tests.

The [Day 24: Scheduling and Persistent Scripts](./Week5/day-24/automation-tool/README.md) schedules
the retail sales reporter to run daily through Windows Task Scheduler or Unix
cron. It includes setup and maintenance utilities, audit logging, and tests.

The [Day 25: Automation Tool for Business Problems](./Week5/day-25/invoice-reminder/README.md)
scans an Excel or CSV invoice register for overdue unpaid records, drafts
polite, tiered follow-up emails with Kenyan payment details (M-Pesa and bank transfer),
and outputs ready-to-dispatch `.txt` files into an `Outbox/` directory.

### Week 6: Advanced AI Applications

The [Day 26: Working With Documents](./Week6/day-26/document-handler/README.md)
extracts PDF text, analyzes contract details with Gemini, creates Word reports,
and indexes invoice PDFs. The separate [PDF Q&A assistant](./Week6/day-26/pdf-Q&A/README.md)
answers questions about a PDF using Gemini, with page citations and support for
scanned documents.

The [Day 27: Multi-Step AI Workflow](./Week6/day-27/workflow/README.md) plans topic
research, gathers Wikipedia references and optional Gemini Search grounding,
synthesizes findings, and produces a professional Markdown brief. It includes
CLI options for audience, tone, model selection, and saving output.

**Day 28: Productizing My AI Application**

## Repository structure

```text
AI-Masterclass-II/
├── render.yaml                     # Render deployment for the Day 18 tracker
├── browser-api-call/               # Country Info HTML page and local API proxy
├── email-drafter/                  # Gemini-powered email drafting CLI
├── news-api/                       # NewsAPI service and browser reader
├── rest-country-api/               # Country information CLI
├── travel-app/                     # Weather and country-profile report
├── weather-app/                    # Settlement and weather CLI
├── Week2/
│   ├── dairy-price-checker/         # Dairy delivery and payment PWA
│   ├── Day6.txt                     # AI-agent client brief
│   ├── Day7.txt                     # AI-agent workflow proposal
│   ├── Day8.txt                     # Dashboard handoff
│   └── day9.txt                     # Attendance-SMS agreement
├── Week3/
│   ├── day-11/                     # My First AI API Call
│   ├── day-12/                     # Prompt Engineering For Developers
│   ├── day-13/                     # Building a Chatbot
│   └── day-14/                     # Function Calling And AI Agents
├── Week4/
│   ├── day-16/                     # Flask Basics
│   ├── day-17/                     # Building a REST API
│   │   ├── README.md               # Sample Orders API
│   │   ├── restapi.py
│   │   └── today's_exercise/       # Poultry egg-production manager
│   ├── day-18/                     # Connecting Frontend and Backend
│   │   └── full-stack/             # Flask egg-production tracker
│   ├── day-19/                     # Deploying My Application
│   │   └── README.md               # Egg tracker overview and Kenyan SME analysis
│   └── day-20/                     # Deployed AI Web Application
│       ├── app.py                  # Flask web backend & Gemini reply generator
│       ├── templates/index.html    # Single-page WhatsApp reply interface
│       ├── test_app.py             # Integration & AI quality test suite
│       ├── render.yaml             # Render blueprint configuration
│       ├── requirements.txt        # Python package dependencies
│       └── README.md               # Tool overview & Kenyan SME client pricing strategy
├── Week5/
│   ├── day-21/                     # File Automation
│   │   ├── file-automation/        # Safe file automation CLI
│   │   └── law-firm-sorter/        # Extension-based legal document sorter
│   ├── day-22/                     # Web Scraping Basics
│   │   ├── job-market-tracker/     # Competitor job market & skills tracking pipeline
│   │   └── web-scraper/            # Books to Scrape web scraper and CSV exporter
│   ├── day-23/                     # Email and Notification Automation
│   │   ├── email-automation/       # SMTP email and scheduled report examples
│   │   └── retail-sales-reporter/  # Daily sales metrics and low-stock email report
│   ├── day-24/                     # Scheduling and Persistent Scripts
│   │   └── automation-tool/        # Scheduled retail reporter and audit logging
│   └── day-25/                     # Automation Tool for Business Problems
│       └── invoice-reminder/       # Automated invoice reminder and outbox drafter
└── Week6/
    ├── day-26/                     # Working With Documents
    │   ├── document-handler/       # PDF processing and Word report examples
    │   └── pdf-Q&A/                # Gemini-powered PDF question-answering CLI
    └── day-27/                     # Multi-Step AI Workflow
        └── workflow/               # Gemini research-to-brief CLI
```

## Getting started

Choose a project and follow its README for project-specific dependencies,
credentials, and commands. Python version and installation steps may differ
between projects. Some applications call external services and require API
keys; configure them through environment variables or a local `.env` file as
described in the relevant project documentation.

Keep API keys, passwords, customer conversations, and other private data out
of source control. Do not commit `.env` files or generated data unless a
project specifically requires a safe sample.

## Author

Branham Simiyu
