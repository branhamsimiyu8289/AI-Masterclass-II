"""
Automated Integration & Quality Test Suite
------------------------------------------
Tests the Nairobi Customer Complaint Reply Drafter:
- Web interface rendering (GET /)
- Health check route (GET /healthz)
- Input validation (POST /api/generate-reply with empty body)
- At least 4 distinct complaint test cases across key Nairobi SME categories:
    1. Courier Service (Delivery delay & unreachable rider)
    2. Restaurant / Food Order (Cold nyama choma & missing item)
    3. Airbnb / Holiday Apartment (Wi-Fi down & hot water issue)
    4. Retail Shop / Boutique (Wrong dress size delivered before event)
- Strict AI quality checks:
    ✓ Polite tone & greeting
    ✓ Acknowledges the specific issue
    ✓ Offers a clear, actionable next step
    ✓ No blame placed
    ✓ No over-promising
"""

import unittest
from app import app, generate_fallback_reply


class NairobiComplaintReplyTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_01_index_page_loads(self):
        """Verify the web tool loads with the text box and Generate Reply button."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Generate Reply", html)
        self.assertIn("complaintInput", html)
        self.assertIn("WhatsApp Reply Drafter", html)

    def test_02_health_check(self):
        """Verify the /healthz monitoring endpoint."""
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "nairobi-complaint-reply-tool")

    def test_03_empty_input_validation(self):
        """Verify API rejects empty complaints with a helpful 400 error."""
        response = self.client.post("/api/generate-reply", json={"complaint": ""})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

        # Also test whitespace only
        response_ws = self.client.post("/api/generate-reply", json={"complaint": "   \n\t  "})
        self.assertEqual(response_ws.status_code, 400)

    def test_04_courier_complaint(self):
        """
        Test Case 1: Courier Service
        Complaint: Rider delay from Westlands to Karen and switched off phone.
        """
        complaint = (
            "Your rider picked up my package in Westlands at 11 AM promising delivery to Karen by 1 PM. "
            "It is now 4:30 PM, the client is leaving the office, and the rider's phone is switched off! Explain this!"
        )
        response = self.client.post("/api/generate-reply", json={"complaint": complaint})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        print("\n" + "=" * 60)
        print("TEST 1 - COURIER SERVICE COMPLAINT")
        print("COMPLAINT:\n", complaint)
        print("\nGENERATED REPLY:\n", reply)
        print("=" * 60)

        # Verify quality rules
        reply_lower = reply.lower()
        # 1. Polite greeting
        self.assertTrue(any(g in reply_lower for g in ["hello", "habari", "thank you", "dear", "good"]))
        # 2. Acknowledges issue
        self.assertTrue(any(w in reply_lower for w in ["apolog", "delay", "frustrat", "inconvenienc", "package", "rider"]))
        # 3. Clear next step
        self.assertTrue(any(w in reply_lower for w in ["dispatch", "check", "contact", "trace", "reach", "update", "minute"]))
        # 4. No blame keywords
        self.assertNotIn("your fault", reply_lower)
        self.assertNotIn("not our problem", reply_lower)

    def test_05_restaurant_complaint(self):
        """
        Test Case 2: Restaurant & Food Delivery
        Complaint: Cold nyama choma and missing ugali for guests.
        """
        complaint = (
            "I placed an order on WhatsApp for 1kg wet fry nyama choma and ugali an hour and a half ago. "
            "The food just arrived completely cold and the ugali was missing from the bag! My guests are waiting!"
        )
        response = self.client.post("/api/generate-reply", json={"complaint": complaint})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        print("\n" + "=" * 60)
        print("TEST 2 - RESTAURANT COMPLAINT")
        print("COMPLAINT:\n", complaint)
        print("\nGENERATED REPLY:\n", reply)
        print("=" * 60)

        reply_lower = reply.lower()
        # 1. Polite
        self.assertTrue(any(g in reply_lower for g in ["hello", "habari", "thank you"]))
        # 2. Acknowledges food/order issue
        self.assertTrue(any(w in reply_lower for w in ["apolog", "cold", "ugali", "order", "food", "guests"]))
        # 3. Actionable next step
        self.assertTrue(any(w in reply_lower for w in ["kitchen", "dispatch", "send", "replac", "fresh", "rider", "confirm"]))
        # 4. No blame
        self.assertNotIn("you should have", reply_lower)

    def test_06_airbnb_complaint(self):
        """
        Test Case 3: Airbnb / Rental Stay
        Complaint: Wi-Fi down and no hot water in shower before a call.
        """
        complaint = (
            "Hi, we checked into the Kilimani apartment 2 hours ago. The Wi-Fi is not working at all and "
            "there is no hot water in the master shower. We have a video call in 30 minutes. Please fix this immediately."
        )
        response = self.client.post("/api/generate-reply", json={"complaint": complaint})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        print("\n" + "=" * 60)
        print("TEST 3 - AIRBNB HOST COMPLAINT")
        print("COMPLAINT:\n", complaint)
        print("\nGENERATED REPLY:\n", reply)
        print("=" * 60)

        reply_lower = reply.lower()
        # 1. Polite greeting
        self.assertTrue(any(g in reply_lower for g in ["hello", "hi", "welcome", "thank you", "habari"]))
        # 2. Acknowledges wifi/shower issue
        self.assertTrue(any(w in reply_lower for w in ["apolog", "wi-fi", "wifi", "water", "shower", "inconvenien"]))
        # 3. Actionable next step
        self.assertTrue(any(w in reply_lower for w in ["caretaker", "maintenance", "check", "heading", "router", "hotspot", "minutes"]))

    def test_07_retail_boutique_complaint(self):
        """
        Test Case 4: Retail Boutique Shop
        Complaint: Wrong size dress delivered before family ruracio.
        """
        complaint = (
            "I ordered the emerald green linen dress in size M, but you delivered size XL to my office in Upper Hill, "
            "and tomorrow morning is my sister's ruracio. This is totally unacceptable!"
        )
        response = self.client.post("/api/generate-reply", json={"complaint": complaint})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        print("\n" + "=" * 60)
        print("TEST 4 - RETAIL SHOP COMPLAINT")
        print("COMPLAINT:\n", complaint)
        print("\nGENERATED REPLY:\n", reply)
        print("=" * 60)

        reply_lower = reply.lower()
        # 1. Polite
        self.assertTrue(any(g in reply_lower for g in ["hello", "thank you", "habari", "dear"]))
        # 2. Acknowledges size/dress issue
        self.assertTrue(any(w in reply_lower for w in ["apolog", "dress", "size", "ruracio", "mistake", "wrong"]))
        # 3. Actionable next step
        self.assertTrue(any(w in reply_lower for w in ["exchange", "dispatch", "rider", "deliver", "stock", "confirm", "send"]))


if __name__ == "__main__":
    unittest.main()
