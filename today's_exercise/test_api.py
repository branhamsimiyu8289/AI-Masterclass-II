import unittest

import httpx

from main import app, records


class EggApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        records.clear()
        transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def add_record(self, shed, day, count):
        return await self.client.post(
            "/api/eggs",
            json={"shed": shed, "date": day, "count": count},
        )

    async def test_openapi_describes_api(self):
        response = await self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["title"], "Egg Production Log")

    async def test_create_normalizes_shed_name(self):
        response = await self.add_record("  Shed   A  ", "2026-11-03", 412)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"id": 1, "shed": "Shed A", "date": "2026-11-03", "count": 412},
        )

    async def test_invalid_records_are_rejected(self):
        invalid_records = [
            {"shed": "Shed A", "date": "2026-11-03", "count": -1},
            {"shed": "   ", "date": "2026-11-03", "count": 1},
            {"shed": "Shed A", "date": "not-a-date", "count": 1},
            {"shed": "Shed A", "date": "2026-11-03", "count": 100001},
        ]

        for entry in invalid_records:
            with self.subTest(entry=entry):
                response = await self.client.post("/api/eggs", json=entry)
                self.assertEqual(response.status_code, 422)

        self.assertEqual(records, [])

    async def test_list_sorts_and_reports_totals(self):
        await self.add_record("Shed A", "2026-11-05", 398)
        await self.add_record("Shed B", "2026-11-03", 388)
        await self.add_record("Shed A", "2026-11-03", 412)
        await self.add_record("Shed C", "2026-11-04", 120)

        response = await self.client.get("/api/eggs")
        result = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(r["date"], r["running_total"]) for r in result["records"]],
            [
                ("2026-11-03", 388),
                ("2026-11-03", 800),
                ("2026-11-04", 920),
                ("2026-11-05", 1318),
            ],
        )
        self.assertEqual(result["total"], 1318)
        self.assertEqual(
            result["totals_by_shed"],
            {"Shed A": 810, "Shed B": 388, "Shed C": 120},
        )
        self.assertEqual(result["record_count"], 4)

    async def test_date_filters_include_boundaries(self):
        await self.add_record("Shed A", "2026-11-03", 10)
        await self.add_record("Shed A", "2026-11-04", 20)
        await self.add_record("Shed B", "2026-11-05", 30)

        response = await self.client.get(
            "/api/eggs",
            params={"start": "2026-11-04", "end": "2026-11-04"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 20)
        self.assertEqual(response.json()["record_count"], 1)

    async def test_weekly_summary_and_commercial_trays(self):
        # 61 eggs = 2 full trays (30 eggs/tray) + 1 loose
        await self.add_record("Shed 1", "2026-11-03", 61)
        # 30 eggs = 1 full tray + 0 loose
        await self.add_record("Shed 2", "2026-11-04", 30)

        response = await self.client.get("/api/eggs/weekly-summary", params={"end_date": "2026-11-04"})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_eggs"], 91)
        self.assertEqual(data["total_trays"], 3)  # 91 // 30 = 3
        self.assertEqual(data["loose_eggs"], 1)   # 91 % 30 = 1
        self.assertIn("Shed 1", data["by_shed"])
        self.assertEqual(data["by_shed"]["Shed 1"]["trays"], 2)
        self.assertEqual(data["by_shed"]["Shed 1"]["loose"], 1)
        self.assertIn("KIAMBU POULTRY FARM", data["whatsapp_message"])
        self.assertTrue(data["whatsapp_url"].startswith("https://api.whatsapp.com/send?text="))

    async def test_delete_record(self):
        res = await self.add_record("Shed A", "2026-11-03", 50)
        record_id = res.json()["id"]

        del_res = await self.client.delete(f"/api/eggs/{record_id}")
        self.assertEqual(del_res.status_code, 200)

        # Ensure record was removed
        get_res = await self.client.get("/api/eggs")
        self.assertEqual(get_res.json()["records"], [])
        self.assertEqual(get_res.json()["total"], 0)

    async def test_dashboard_serves_html(self):
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Kiambu Poultry Farm", response.text)


if __name__ == "__main__":
    unittest.main()
