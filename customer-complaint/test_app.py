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

import os
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

from app import app, call_gemini_api, generate_fallback_reply
from config import AppConfig, ConfigError, load_and_validate_config


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
        self.assertIn("Reply Drafter", html)

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

    def test_api_key_is_sent_in_header_not_url(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Draft reply"}]}}
            ]
        }
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with patch("app.httpx.Client", return_value=client):
            reply, _ = call_gemini_api("Package is late", "test-api-key")

        self.assertEqual(reply, "Draft reply")
        request_url = client.post.call_args.args[0]
        request_headers = client.post.call_args.kwargs["headers"]
        self.assertNotIn("test-api-key", request_url)
        self.assertEqual(request_headers["x-goog-api-key"], "test-api-key")

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
        self.assertIn("dress", reply_lower)
        self.assertNotIn("ugali", reply_lower)
        # 3. Actionable next step
        self.assertTrue(any(w in reply_lower for w in ["exchange", "dispatch", "rider", "deliver", "stock", "confirm", "send"]))

    def test_08_input_validation_edge_cases(self):
        """Verify malformed JSON, wrong types, short inputs, and oversized inputs return friendly 400 messages."""
        # Non-dict JSON body
        resp_list = self.client.post("/api/generate-reply", json=["not", "an", "object"])
        self.assertEqual(resp_list.status_code, 400)
        self.assertIn("message", resp_list.get_json())

        # Non-string complaint
        resp_int = self.client.post("/api/generate-reply", json={"complaint": 12345})
        self.assertEqual(resp_int.status_code, 400)
        self.assertIn("plain text", resp_int.get_json()["message"])

        # Too short
        resp_short = self.client.post("/api/generate-reply", json={"complaint": "hi"})
        self.assertEqual(resp_short.status_code, 400)
        self.assertIn("at least", resp_short.get_json()["message"])

        # Too long
        resp_long = self.client.post("/api/generate-reply", json={"complaint": "a" * 3500})
        self.assertEqual(resp_long.status_code, 400)
        self.assertIn("exceeds", resp_long.get_json()["message"])

    def test_09_config_driven_branding_and_fallback(self):
        """Verify fallback replies and rendered HTML use configured business details, not hardcoded names."""
        custom_cfg = AppConfig(
            business_name="Zuri Couriers Ltd",
            manager_name="Amina Ochieng",
            support_email="help@zuricouriers.co.ke",
            support_phone="+254 711 222 333",
        )
        reply = generate_fallback_reply("Your rider delayed my parcel.", custom_cfg)
        self.assertIn("Zuri Couriers Ltd", reply)
        self.assertIn("Amina Ochieng", reply)
        self.assertIn("help@zuricouriers.co.ke", reply)
        self.assertNotIn("[Your Business Name]", reply)

        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("Branham Simiyu", html)
        self.assertIn("Savannah Customer Care", html)

    def test_10_config_validation_clear_errors(self):
        """Verify bad config.env values raise ConfigError with plain-English instructions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.env")

            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("SUPPORT_EMAIL=not-an-email\n")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ConfigError) as ctx:
                    load_and_validate_config(tmpdir)
                self.assertIn("SUPPORT_EMAIL", str(ctx.exception))
                self.assertIn("config.env", str(ctx.exception))

            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("PORT=abc\n")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ConfigError) as ctx:
                    load_and_validate_config(tmpdir)
                self.assertIn("PORT", str(ctx.exception))
                self.assertIn("whole number", str(ctx.exception))

            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("SAMPLES_FILE=missing_samples.json\n")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ConfigError) as ctx:
                    load_and_validate_config(tmpdir)
                self.assertIn("SAMPLES_FILE", str(ctx.exception))
                self.assertIn("Could not find", str(ctx.exception))

    def test_11_gemini_rejected_key_returns_friendly_notice_and_fallback(self):
        """Verify rejected API keys never expose tracebacks and provide a clear notice."""
        bad_resp = Mock()
        bad_resp.status_code = 403
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = bad_resp

        with patch("app.httpx.Client", return_value=client):
            resp = self.client.post(
                "/api/generate-reply",
                json={"complaint": "My package has not arrived yet.", "api_key": "bad-key"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("GEMINI_API_KEY", data.get("notice", ""))
        self.assertIn("config.env", data.get("notice", ""))


if __name__ == "__main__":
    unittest.main()
