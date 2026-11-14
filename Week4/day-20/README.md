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

## 🚀 Live Demo & Render Deployment Guide

The project is packaged for deployment to **Render** as a Python Web Service.

### Option 1: Deploy via Render Web Service (Recommended)

1. Sign in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository (`AI-Masterclass-II`).
4. Configure the service settings:
   - **Name**: `nairobi-complaint-reply-tool` (or your preferred name)
   - **Region**: Frankfurt / Oregon (default)
   - **Branch**: `main`
   - **Root Directory**: `Week4/day-20`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`
5. In **Environment Variables**, add:
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `PORT`: `10000` (Render default)
6. Under **Advanced**, set **Health Check Path** to `/healthz`.
7. Click **Create Web Service**. Render will build and deploy your app with a public `https://<service-name>.onrender.com` URL.

### Option 2: Deploy via Render Blueprint (`render.yaml`)

The included [`render.yaml`](./render.yaml) allows one-click infrastructure-as-code deployment:
```yaml
services:
  - type: web
    name: nairobi-complaint-reply-tool
    runtime: python
    plan: free
    rootDir: Week4/day-20
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    healthCheckPath: /healthz
    envVars:
      - key: GEMINI_API_KEY
        sync: false
      - key: PORT
        value: 10000
```

---

## 🧪 Verified Test Cases & Model Outputs

The tool was tested against realistic complaint scenarios drawn directly from common Nairobi small business operations:

### Test Case 1: Nairobi Courier Service
* **Incoming WhatsApp Complaint**:
  > *"Your rider picked up my package in Westlands at 11 AM promising delivery to Karen by 1 PM. It is now 4:30 PM, the client is leaving the office, and the rider's phone is switched off! Explain this!"*

* **Generated WhatsApp Reply Draft**:
  > Habari [Customer Name], and sincere apologies for the deep frustration and inconvenience this delay has caused you and your client in Karen.
  >
  > I completely understand how critical this 1 PM timeline was, and having the rider unreachable is completely unacceptable. Please rest assured that we are taking full ownership of this situation right now.
  >
  > I am immediately reaching out to our dispatch desk to trace the rider's last live coordinates and will call you back within the next 10 minutes with a concrete update on the package's exact location. Thank you for your patience as we sort this out urgently.
  >
  > Warm regards,  
  > [Manager Name]  
  > [Business Name]

* **Verification**:
  - [x] Polite greeting (*Habari [Customer Name]*)
  - [x] Acknowledges Westlands to Karen delay & unreachable phone
  - [x] Zero blame placed (no blaming traffic or rider)
  - [x] No wild over-promising
  - [x] Clear next step (*tracing coordinates & calling back within 10 minutes*)

---

### Test Case 2: Restaurant & Food Delivery
* **Incoming WhatsApp Complaint**:
  > *"I placed an order on WhatsApp for 1kg wet fry nyama choma and ugali an hour and a half ago. The food just arrived completely cold and the ugali was missing from the bag! My guests are waiting!"*

* **Generated WhatsApp Reply Draft**:
  > Habari [Customer Name], thank you for reaching out to us, and sincere apologies for this disappointing experience. I completely understand how frustrating it is to receive cold food and a missing item, especially when you have guests waiting.
  >
  > Please rest assured that we are taking full responsibility for this mix-up. I am having a fresh, hot portion of wet fry nyama choma prepared immediately, along with your ugali, and dispatching it on priority with our head rider right now.
  >
  > We truly appreciate your patience, and we will ensure this reaches you urgently. I will share the rider's live updates with you shortly.
  >
  > Warm regards,  
  > [Manager Name]  
  > [Business Name]

* **Verification**:
  - [x] Polite and empathetic
  - [x] Acknowledges cold food and missing ugali with guests waiting
  - [x] Zero blame placed on kitchen or courier
  - [x] Actionable next step (*fresh portion dispatched on priority with live rider update*)

---

### Test Case 3: Airbnb / Serviced Apartment Host
* **Incoming WhatsApp Complaint**:
  > *"Hi, we checked into the Kilimani apartment 2 hours ago. The Wi-Fi is not working at all and there is no hot water in the master shower. We have a video call in 30 minutes. Please fix this immediately."*

* **Generated WhatsApp Reply Draft**:
  > Habari [Customer Name], thank you for reaching out to us, and sincere apologies for the frustration this is causing, especially right before your important video call.
  >
  > We completely understand how stressful it is to lack Wi-Fi and hot water upon arrival, and we are taking this up right away to get everything sorted out for you as quickly as possible.
  >
  > We are dispatching our technician to your unit immediately to check the router and reset the water heater. I am also monitoring this closely and will update you in the next 10 minutes once they arrive at your door.
  >
  > Thank you for your patience,  
  > [Manager Name]  
  > [Business Name]

* **Verification**:
  - [x] Warm greeting
  - [x] Empathises with 30-minute urgent call pressure
  - [x] Clear next step (*technician dispatched immediately, 10-minute arrival follow-up*)

---

### Test Case 4: E-Commerce Boutique / Retail Shop
* **Incoming WhatsApp Complaint**:
  > *"I ordered the emerald green linen dress in size M, but you delivered size XL to my office in Upper Hill, and tomorrow morning is my sister's ruracio. This is totally unacceptable!"*

* **Generated WhatsApp Reply Draft**:
  > Habari [Customer Name], thank you for reaching out, and I am so deeply sorry for the stress and inconvenience this wrong delivery has caused, especially given that your sister's ruracio is tomorrow morning. We completely understand how important this outfit is for the big day, and we take full responsibility for this mix-up.
  >
  > We want to fix this immediately. I am coordinating with our dispatch team right away to arrange an express swap, bringing the correct size M emerald green linen dress directly to your office in Upper Hill this afternoon.
  >
  > Could you please confirm the exact office building name or reception details so our rider heads straight there without delay? We are on it right now.
  >
  > Warm regards,  
  > [Manager Name]  
  > [Business Name]

* **Verification**:
  - [x] Empathetic cultural awareness (*ruracio event context*)
  - [x] Full responsibility taken
  - [x] Immediate express swap arranged with specific office confirmation request

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
