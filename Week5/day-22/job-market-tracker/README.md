# Competitor Job Market Tracker (Nairobi HR Intelligence)

Automated competitor job posting scraper and talent intelligence pipeline designed for HR managers and recruitment consultancies in Nairobi.

---

## 1. Business Problem Scenario

In Nairobi's competitive hiring market—spanning technology hubs in Westlands and Kilimani to banking and insurance headquarters in Upper Hill—mid-size companies face intense competition for talent. 

HR managers routinely monitor competitor career portals and job boards to answer critical questions:
- **Skill Demand**: Which new frameworks, cloud certifications, or regulatory skills are competitors requiring?
- **Compensation Benchmarking**: What salary ranges, perks, or flexible-work terms are competing firms advertising?
- **Hiring Surges & Attrition Signals**: Is a competitor rapidly expanding their engineering team or replacing key senior staff?

Currently, HR teams do this manually: junior analysts open dozens of browser tabs each Monday, copying role titles, requirements, and salary figures into spreadsheets. This process is time-consuming, prone to human error, and misses short-lived postings. This automated solution converts manual browsing into an automated, structured data pipeline.

---

## 2. Sandbox Prototype

Live recruitment platforms and LinkedIn aggressively rate-limit or block unauthorized bots with CAPTCHAs. To demonstrate the extraction architecture safely, this prototype targets **[quotes.toscrape.com](https://quotes.toscrape.com/)**, an authorized public scraping sandbox.

### Extracted Data Fields

The scraper extracts five structured fields per item, mapping directly to HR market tracking metrics:

| Extracted Field | Prototype Field | HR Market Mapping |
|---|---|---|
| `text` | Quote text | Job description summary / responsibilities overview |
| `author` | Author name | Hiring organization / competitor name |
| `tags` | Comma-separated tags | In-demand technical and soft skills |
| `tag_count` | Tag count | Skill density / role complexity indicator |
| `author_url` | Full profile link | Canonical URL to listing / employer profile |

Data is saved to [`job_listings.csv`](./job_listings.csv) with UTF-8 encoding.

---

## 3. How to Run the Prototype

### Prerequisites
- Python 3.10+
- Dependencies in [`requirements.txt`](./requirements.txt):
  ```bash
  python -m pip install -r requirements.txt
  ```

### CLI Execution
Run the scraper directly:
```bash
python scraper.py
```

### CLI Options
Custom page counts, politeness delays, and output paths can be configured:
```bash
# Scrape 3 pages with a 2-second delay between pages
python scraper.py --pages 3 --delay 2.0 --output competitor_jobs.csv
```

### Example Terminal Output
```text
[*] Starting job market scrape from: https://quotes.toscrape.com
[*] Target max pages: 3 | Inter-request delay: 1.0s

[*] Fetching Page 1: https://quotes.toscrape.com
[+] Found 10 listings on Page 1

[*] Fetching Page 2: https://quotes.toscrape.com/page/2/
[+] Found 10 listings on Page 2

[*] Fetching Page 3: https://quotes.toscrape.com/page/3/
[+] Found 10 listings on Page 3

[✓] Successfully scraped 30 total listings across 3 pages.
[✓] Saved data to: C:\Users\...\job_listings.csv
```

---

## 4. Adapting for a Client-Authorized Live Jobs Board

When transitioning from the sandbox to a private or client-authorized recruitment board, the following adaptations are required:

1. **Authentication & Session Management**:
   - Configure authenticated sessions (`requests.Session()`) supporting form-based login, session cookies, API tokens, or OAuth2 headers.
   - Implement automatic re-authentication when session tokens expire.

2. **Handling JavaScript-Rendered Content (SPAs)**:
   - Modern job boards (e.g., built with React, Vue, or Next.js) load jobs dynamically via asynchronous API calls.
   - **Preferred Approach**: Inspect network traffic via DevTools to query the board's internal REST/GraphQL API directly (faster, lighter, more reliable than DOM parsing).
   - **Alternative**: Use Playwright or headless Chromium if pages rely on complex DOM hydration or dynamic infinite scrolling.

3. **Data Normalization & Salary Parsing**:
   - Implement regular expressions to parse Kenyan salary formats (e.g., `KSh 120,000 - KSh 180,000 per month`, `KES 2.4M gross/annum`).
   - Standardize seniority levels (`Junior`, `Mid-Level`, `Senior`, `Lead`, `Head of`) and work models (`Remote`, `Hybrid`, `On-site Nairobi`).

4. **Change Detection (Deduplication & Diffing)**:
   - Generate unique hashes of job IDs and descriptions.
   - Store historical scrapes in SQLite or PostgreSQL to detect **New Postings**, **Updated Requirements**, and **Closed/Filled Roles** week-over-week.

5. **Automated Report Generation**:
   - Aggregate top skills demanded (e.g., Python, AWS, Docker, IFRS9).
   - Automatically compile a branded weekly Excel report with pivot tables and a 2-page PDF executive summary sent via email or Slack.

---

## 5. Ethical and Legal Considerations

Before executing web scrapers against any commercial or external job site, the following legal and operational controls must be verified:

1. **Terms of Service (ToS) & Authorization**:
   - Review the target site's Terms of Use. If scraping an authenticated client portal, ensure explicit written client authorization is documented in the engagement contract.
2. **`robots.txt` and Crawl Directives**:
   - Check `https://<domain>/robots.txt` for disallowed directories and respect `Crawl-delay` parameters.
3. **Kenya Data Protection Act (KDPA 2019)**:
   - Job listings themselves are public business advertisements; however, personal data (such as recruiter names, direct mobile numbers, and personal email addresses) falls under the KDPA 2019.
   - Scrapers must sanitize or omit personal contact details, storing only organizational data (company, title, requirements, salary).
4. **Server Load & Rate Limiting (Polite Crawling)**:
   - Implement rate limits (1–3 second jittered intervals) and run scrapes during off-peak hours (e.g., 2:00 AM – 4:00 AM EAT) to prevent degrading server performance for genuine job seekers.
5. **API-First Rule**:
   - Always inquire whether the platform offers an official partner API, RSS feed, or data export before writing HTML scraping rules.

---

## 6. Commercial Pricing Note (HR Consultancy Client)

For an HR consultancy or corporate talent acquisition team in Nairobi requiring weekly competitor market monitoring and clean report delivery:

### 1. One-Time Setup & Deployment Fee: **KSh 50,000** (~$390 USD)
- **Scope**:
  - Target site discovery, HTML/API structure inspection, and authentication integration.
  - Custom scraper development with retry logic, rate limiting, and failure alerts.
  - Data schema normalization (salary parsing, skill tagging, deduplication database).
  - Branded weekly Excel/PDF reporting template design.
  - End-to-end testing and initial client handover.

### 2. Monthly Maintenance & Delivery Retainer: **KSh 30,000 / month** (~$235 USD)
- **Scope**:
  - Weekly automated crawl execution (scheduled every Sunday night).
  - Data cleaning, validation, deduplication, and weekly report delivery by Monday 8:00 AM EAT.
  - Scraper maintenance and selector updates when target job portals modify their frontend code or HTML layout.
  - Monthly executive summary highlighting emerging skill shifts and salary trends.

### Return on Investment (ROI)
A mid-level HR analyst earning KSh 80,000/month spends approximately 16 hours per month manually browsing competitor job sites (~KSh 16,000 in direct labor cost), often with inconsistent coverage and transcription errors. At **KSh 30,000/month**, the consultancy receives 100% comprehensive, structured, error-free competitor intelligence delivered on schedule, freeing HR staff to focus on strategic talent acquisition.

---

## Author

**Branham Simiyu**
