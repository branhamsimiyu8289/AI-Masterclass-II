# Kamau Stores Assistant

This project is a customer service chatbot for Kamau Stores, a wholesale distributor in Nairobi. It uses the Google Gemini API to answer questions about:

- orders
- pricing
- delivery

The assistant is designed to stay within a limited scope and respond politely and professionally.

## Features

- Answers questions about orders, pricing, and delivery only
- Uses Gemini for natural language processing
- Accepts only KES pricing language
- Supports delivery in Nairobi, Mombasa, Kisumu, and Nakuru only
- Redirects out-of-scope questions to the office phone number: 0712 345 678
- Ends every response with: "Asante kwa kuwasiliana."

## Requirements

- Python 3.9 or later
- A valid Gemini API key
- Internet access for the Google GenAI API

## Installation

Install the required Python packages:

```bash
pip install httpx python-dotenv google-genai
```

## Environment Setup

Create a `.env` file in the `Week3` directory:

```env
GEMINI_API_KEY=your_api_key_here
```

The script loads the environment file from:

```text
Week3/.env
```

## Run the Program

From the project root, run:

```bash
python "Week3/day-12/Kamau-Stores.py"
```

## Example Conversation

```text
Welcome to Kamau Stores. How can we help? Do you deliver to Nakuru?
```

Example output:

```text
Yes, we deliver to Nakuru. Asante kwa kuwasiliana.
```

```text
Welcome to Kamau Stores. How can we help? Do you deliver to Eldoret?
```

Example output:

```text
Please call our office on 0712 345 678 for that.
Asante kwa kuwasiliana.
```

## Notes

- The bot only answers questions related to orders, pricing, and delivery.
- All prices are treated as Kenyan Shillings (KES).
- Delivery is limited to Nairobi, Mombasa, Kisumu, and Nakuru.
- Any out-of-scope question triggers the office contact response.

## File

- `Week3/day-12/Kamau-Stores.py`
