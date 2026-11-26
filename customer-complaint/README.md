# WhatsApp Customer Complaint Reply Drafter

A single-purpose web tool for small businesses that receive customer complaints on WhatsApp and want calm, polite, professional reply drafts in seconds—customized with your business name, manager name, and contact details via `config.env`.

---

## Setup Guide (For Clients)

**Step 1:** Download the project folder and unzip it to your Desktop or Documents folder.

**Step 2:** Open `config.env` with Notepad, fill in your `BUSINESS_NAME`, `MANAGER_NAME`, `SUPPORT_EMAIL`, `SUPPORT_PHONE` (and optionally your `GEMINI_API_KEY`—leave it blank to use the built-in offline engine), then save and close the file.

**Step 3:** Double-click `run.bat` to start the tool. Your browser will open automatically at `http://127.0.0.1:5000`—paste any customer complaint and click **Generate Reply**.

That is it. You never need to open or edit any Python or HTML code.

---

## Service Description

### What It Does
Turns angry, urgent, or sensitive customer WhatsApp complaints into calm, empathetic, blame-free reply drafts in seconds. Every reply acknowledges the customer's frustration, avoids blaming staff or external conditions, avoids reckless promises, gives a clear next step, and signs off automatically with your business name, manager name, and contact details. It works online with Google Gemini AI and automatically falls back to a built-in offline reply engine if your internet is down or no API key is configured.

### Who It Is For
Small and medium Kenyan businesses that handle customer service over WhatsApp—including courier and boda boda dispatch services, restaurants and food delivery kitchens, Airbnb and short-stay property hosts, and retail boutiques.

### What It Replaces
- Spending 15 to 25 minutes per complaint deciding how to respond under pressure
- Copy-pasting awkward, generic templates from Notes or Word documents
- Inconsistent, defensive, or emotional staff replies that cost repeat customers or risk viral screenshots on social media

### What It Costs
- **Starter Branded Tool:** **KES 30,000 – KES 45,000** one-time setup (custom branding, `config.env` setup, and onboarding) + **KES 3,500 / month** optional maintenance and hosting support.
- **Business Pro (Multi-Department):** **KES 65,000 – KES 90,000** one-time setup + **KES 7,500 – KES 12,000 / month** (multiple department presets, staff access, and monthly complaint analytics).
- **Enterprise WhatsApp Co-Pilot:** **KES 150,000 – KES 250,000** one-time setup + **KES 20,000 – KES 35,000 / month** (WhatsApp Business Cloud API and ERP/order-system integration).
- *Note:* When self-hosted locally via `run.bat` with your own Gemini API key, AI usage runs within Google's free tier or pennies per month—or KES 0 using the built-in offline engine.

---

## Clear Error Messages (No Python Tracebacks)

If a setting in `config.env` or an input is invalid, the tool explains the exact problem in plain language:

| Situation | Message Shown to User |
| :--- | :--- |
| Invalid `SUPPORT_EMAIL` in `config.env` | `"The SUPPORT_EMAIL in config.env ('...') does not look like a valid email address. Please enter an email like support@yourbusiness.co.ke or leave it blank."` |
| Missing `SAMPLES_FILE` in `config.env` | `"Could not find your samples file ('...'). Check that SAMPLES_FILE in config.env points to an existing file, or leave SAMPLES_FILE blank to use built-in examples."` |
| Invalid `PORT` in `config.env` | `"Invalid PORT setting in config.env ('...'). Please enter a whole number between 1 and 65535 (for example, 5000)."` |
| Port already in use | `"Port 5000 is already in use by another program. Close the other window or set PORT=5001 in config.env."` |
| Rejected Gemini API key | `"Your Gemini API key in config.env was rejected. Double-check GEMINI_API_KEY in config.env. Using the built-in offline reply engine for now."` |
| Empty or oversized complaint | `"Please paste or type a customer complaint before clicking Generate Reply."` / `"Your message is ... characters long, which exceeds the 3,000-character limit."` |

---

## Automated Tests (For Developers)

Run the automated test suite from the `customer-complaint` project directory:

```powershell
python test_app.py
```
