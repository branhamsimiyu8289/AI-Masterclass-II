# Nairobi Business WhatsApp Complaint Reply Drafter

A focused, single-purpose web tool designed for small Nairobi businesses—**shops, courier services, Airbnbs, and restaurants**—that receive customer complaints on WhatsApp and want to respond professionally, calmly, and constructively without spending 20 minutes agonising over what to write.

---

## 🎯 What the Tool Does

Small Kenyan enterprises conduct virtually all their daily customer communications on WhatsApp. When a delivery is delayed, food arrives cold, an apartment amenity fails, or the wrong item is delivered, business owners face a critical moment:
- Responding emotionally or defensively drives away loyal clients and risks public exposure on social media.
- Over-promising (e.g. wild refunds or impossible timelines) creates new liabilities.
- Crafting a diplomatic, reassuring reply from scratch often takes 15 to 25 minutes while orders and inquiries pile up.

This tool solves that exact bottleneck with an ultra-minimal, zero-distraction workflow:
1. **One Text Box**: The business operator pastes the customer's complaint directly from WhatsApp.
2. **One Button ("Generate Reply")**: Submits the text to the AI backend.
3. **Instant Professional Draft (On the Same Page)**: Returns a WhatsApp-formatted reply draft ready to copy and send in seconds.

---

## 🛡️ Core AI Response Principles

Every generated draft strictly complies with five non-negotiable customer service rules:

1. **Polite & Respectful**: Initiates with warm, professional Kenyan business etiquette (e.g. *Habari [Customer Name]*, *Hello [Customer Name]*, *Thank you for reaching out to us*).
2. **Direct Acknowledgment with Empathy**: Validates the customer's specific grievance without dismissing or minimising their inconvenience.
3. **Strict No-Blame Policy**: Never passes blame to external factors—no blaming Nairobi traffic, rain, boda riders, suppliers, kitchen staff, or the customer. The business takes calm, dignified ownership.
4. **No Over-Promising**: Avoids reckless commitments or unrealistic instant payouts. Every commitment made is concrete, feasible, and grounded.
5. **Clear, Actionable Next Step**: Provides immediate momentum (e.g., live rider tracing via dispatch desk, express replacement dispatch, on-site technician dispatch within 5–10 minutes).
6. **WhatsApp-Optimized**: Formatted in short, mobile-scannable paragraphs with clean line breaks and placeholders (`[Business Name]`, `[Manager Name]`).

---

## Live Demo

Try the [Nairobi Business WhatsApp Complaint Reply Drafter](https://nairobi-complaint-reply-tool.onrender.com/).

---

## 💼 Commercial Pricing Strategy for Business Clients

This application is built as a commercial-grade portfolio piece for pitching custom AI automations to Kenyan SMEs. Below is the proposed tiered pricing structure when packaging and selling a **branded version** of this tool to a Nairobi business client:

### 1. Tier Breakdown & Service Packages

| Package | Target Client | Scope & Inclusions | One-Off Setup Fee | Monthly Retainer / Maintenance |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Starter Branded Web Tool** | Independent boutique shops, individual Airbnb hosts (1–3 listings), standalone dispatch couriers | - Custom logo, brand colors, and company tone<br>- Pre-configured business contact numbers and refund/exchange policies<br>- Hosted on dedicated custom domain (e.g. `support.yourbrand.co.ke`)<br>- One-click "Copy to WhatsApp" and "Send via WhatsApp" shortcuts | **KES 30,000 – KES 45,000** | **KES 3,500 / month** (includes cloud hosting, uptime monitoring, and API quota) |
| **Tier 2: Business Pro (Multi-Category)** | Multi-branch restaurants (e.g., Westlands + Kilimani), regional couriers (Nairobi & Kiambu), boutique hotel/Airbnb management agencies | - Multiple department presets (Kitchen, Bar, Dispatch, Reception, Maintenance)<br>- Staff multi-seat access (different staff generate drafts matching their department role)<br>- Tone calibration (from casual Kenyan hospitality to formal corporate dispatch)<br>- Monthly analytics on common complaint themes (e.g., rider delays vs. cold food) | **KES 65,000 – KES 90,000** | **KES 7,500 – KES 12,000 / month** |
| **Tier 3: Enterprise WhatsApp Co-Pilot (API Integrated)** | Established logistics companies (e.g., Sendy-style fleets), large e-commerce brands, high-turnover hospitality hubs | - Direct integration with official **WhatsApp Business Cloud API** or shared team inbox (e.g., Respond.io, WATI, Trengo)<br>- In-line draft suggestions appearing automatically inside the agent's chat screen<br>- Integration with ERP / POS to auto-fetch rider coordinates or order status directly into the draft<br>- Dedicated SLA & 24/7 uptime guarantee | **KES 150,000 – KES 250,000** | **KES 20,000 – KES 35,000 / month** |

---

### 2. The Client Value Proposition & ROI Justification

When selling to a Kenyan SME owner, technical jargon must be translated into direct **M-Pesa cash impact**:

1. **Labor Savings**:
   - An average Nairobi courier or restaurant receives 8 to 15 customer complaints per day.
   - Spending 15 minutes per complaint equates to ~3 hours of daily management time.
   - At a manager salary of KES 60,000/month, the tool saves ~KES 25,000/month in reclaimed productive operational time.

2. **Customer Retention Value (LTV)**:
   - Acquiring a repeat restaurant customer or courier contract in Nairobi costs between KES 1,500 and KES 4,000 in social media marketing or referral effort.
   - An angry customer who leaves due to a defensive or rude WhatsApp reply is lost forever.
   - Salvaging just **two high-value customer relationships per month** through a calm, professional, empathetic reply completely covers the tool's entire monthly fee.

3. **Reputation Insurance**:
   - Negative screenshots of defensive WhatsApp replies routinely go viral on Nairobi Twitter/X, Instagram, and local community Facebook groups.
   - A standardized, blame-free response engine acts as brand insurance against public PR crises.

---

## 🛠️ Local Development & Testing

### 1. Requirements
- Python 3.10+
- A Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/apikey))

### 2. Setup
```powershell
cd "C:\Users\owen chole\Desktop\AI-Masterclass II\AI-Masterclass-II\Week4\day-20"
pip install -r requirements.txt
```

### 3. Configure API Key
Copy `.env.example` to `.env`:
```text
GEMINI_API_KEY=your_gemini_api_key_here
PORT=5000
```

### 4. Run the Application
```powershell
python app.py
```
Open your browser at **`http://127.0.0.1:5000`**.

### 5. Run Automated Tests
```powershell
python test_app.py
```
Validates the UI route, health check endpoint, input validation, and executes all 4 live complaint scenarios against the model.
