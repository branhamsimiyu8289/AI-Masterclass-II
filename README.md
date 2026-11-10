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

### Week 2: workflow exercises

[`Week2/`](./Week2/) contains business workflow planning materials: an AI-agent
client brief and proposal, a dashboard handoff, and an attendance-SMS project
agreement.

The [dairy-price-checker](./Week2/dairy-price-checker/) is a FastAPI and SQLite
progressive web app for recording milk deliveries and calculating farmer
payments. It includes a farmer entry page, live price updates, and an admin
dashboard for managing prices and daily records.

### Week 3: Gemini assistants and agents

| Folder | Description |
|---|---|
| [day-11/](./Week3/day-11/) | Command-line question-and-answer program using Google's Gemini API. |
| [day-12/](./Week3/day-12/) | Kamau Stores customer-service assistant and a property inquiry extractor that returns structured JSON. |
| [day-13/](./Week3/day-13/) | Otieno Wholesale chatbot with bounded conversation context and a local transcript; includes a [Kisumu Pharmacy chatbot](./Week3/day-13/Kisumu-Pharmacy-Chatbot/) for staff support and contextual follow-up questions. |
| [day-14/](./Week3/day-14/) | Gemini tool-calling inventory and price assistant for Kamau Stores, plus the [Kericho tea harvesting agent](./Week3/day-14/Kericho-AI-agent-tool/) that checks weather and the six-hour rain forecast before recommending whether to harvest. |

### Week 4: customer balance lookup

The [day-16 project](./Week4/day-16/) is a small Flask web app for looking up
sample customer credit balances at an Eldoret hardware shop. Search by customer
name in the browser or use the JSON API. It demonstrates a simple business
lookup workflow using an HTML form, a Flask endpoint, and hardcoded sample
balances. Its project README covers the problem, solution, features, setup, run
instructions, and example output.

The [day-17 project](./Week4/day-17/) is a Flask Orders API for listing,
creating, and looking up sample orders, as well as updating order statuses.
Orders are stored in memory and reset when the server restarts. See the
[project README](./Week4/day-17/README.md) for setup and example requests.

## Repository structure

```text
AI-Masterclass-II/
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
│   ├── day-11/                     # Gemini Q&A
│   ├── day-12/                     # Store assistant and property extraction
│   ├── day-13/                     # Wholesale and pharmacy chatbots
│   └── day-14/                     # Inventory and tea harvesting agents
└── Week4/
    ├── day-16/                     # Hardware shop customer balance lookup
    └── day-17/                     # Sample Orders API
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
