# AI Masterclass II: Automation and Automization

This repository brings together projects, coding exercises, and planning
materials from **AI Masterclass II: Automation and Automization**. The work
explores how Python, APIs, web applications, and AI assistants can automate
information lookup, customer support, data entry, and everyday business
workflows. Projects are organized by topic and course week; each application is
independent and has its own setup requirements.

## Project catalogue

### API and information lookup

| Project | What it does |
|---|---|
| [browser-api-call/](./browser-api-call/) | Browser-based country lookup. A local Python server keeps the REST Countries API credential out of the browser and serves the lookup page. |
| [rest-country-api/](./rest-country-api/) | Python CLI that looks up a country's capital, population, and currency through the REST Countries API. |
| [weather-app/](./weather-app/) | CLI that validates settlement names and displays current weather and local sunrise/sunset times using OpenStreetMap Nominatim and OpenWeather. |
| [travel-app/](./travel-app/) | Travel weather and location tool that accepts place names or GPS coordinates, enriches weather data with a country profile, and exports a JSON report. |
| [news-api/](./news-api/) | FastAPI-backed news reader with a browser interface for politics, weather, sports, and agriculture headlines from NewsAPI. |

### Week 2: workflow exercises and dairy price checker

[`Week2/`](./Week2/) contains course notes and business workflow exercises,
including an AI-agent client brief and proposal, a dashboard handoff, and an
attendance-SMS project agreement.

The [dairy-price-checker/](./Week2/dairy-price-checker/) is a FastAPI and
SQLite-backed progressive web app for recording milk deliveries and calculating
farmer payments. It includes a farmer entry page, live price updates, and an
admin dashboard for setting prices and reviewing or deleting daily records.

### Week 3: Gemini assistants and automation exercises

| Folder | What it does |
|---|---|
| [day-11/](./Week3/day-11/) | Gemini-powered command-line question-and-answer script. |
| [day-12/](./Week3/day-12/) | A Kamau Stores customer-service assistant and a property inquiry extractor that returns structured JSON. |
| [day-13/](./Week3/day-13/) | Otieno Wholesale conversational assistant with bounded context and a local conversation log; also includes the [Kisumu Pharmacy chatbot](./Week3/day-13/Kisumu-Pharmacy-Chatbot/) for staff support and contextual follow-up questions. |

## Repository structure

```text
AI-Masterclass-II/
├── browser-api-call/               # Browser country lookup with local API proxy
├── news-api/                       # NewsAPI backend and browser news reader
├── rest-country-api/               # Country information CLI
├── travel-app/                     # Weather, GPS, and country-profile report
├── weather-app/                    # Settlement and weather CLI
├── Week2/
│   ├── dairy-price-checker/         # Dairy delivery and payment PWA
│   ├── Day6.txt                    # AI-agent client brief
│   ├── Day7.txt                    # AI-agent workflow proposal
│   ├── Day8.txt                    # Dashboard handoff message
│   └── day9.txt                    # Attendance SMS project agreement
└── Week3/
    ├── day-11/                     # Gemini Q&A
    ├── day-12/                     # Store assistant and property extraction
    └── day-13/                     # Wholesale and pharmacy chatbots
```

## Getting started

There is no single dependency file or run command for the whole repository.
Choose a project and follow its README for dependencies, API credentials, and
run instructions. Some projects require third-party API keys; provide them
through environment variables or a local `.env` file as described by that
project.

Keep API keys, passwords, customer conversations, and other private data out
of source control. Do not commit `.env` files or generated data unless a
project specifically requires a safe sample.
