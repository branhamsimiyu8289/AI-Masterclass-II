import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

api_key = os.getenv("RESTCOUNTRIES_API_KEY")
if not api_key:
    raise RuntimeError("RESTCOUNTRIES_API_KEY is missing from the .env file.")
print("=======REST COUNTRY APIs=======")
country_name = input("Enter a country: ").strip()
if not country_name:
    print("Please enter a country name.")
else:
    url = (
        "https://api.restcountries.com/countries/v5/names.common/"
        f"{requests.utils.quote(country_name, safe='')}"
    )

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as error:
        print(f"Could not retrieve country data: {error}")
    else:
        country_data = payload.get("data", {}) if isinstance(payload, dict) else {}
        countries = (
            country_data.get("objects", [])
            if isinstance(country_data, dict)
            else []
        )

        if not countries:
            print(f"No country data found for {country_name}.")
        else:
            country = countries[0]
            names = country.get("names", {})
            name = (
                names.get("common", country_name)
                if isinstance(names, dict)
                else country_name
            )

            capitals = country.get("capitals", [])
            capital = (
                capitals[0].get("name", "N/A")
                if capitals and isinstance(capitals[0], dict)
                else "N/A"
            )

            population = country.get("population")
            population_text = (
                f"{population:,}" if isinstance(population, int) else "N/A"
            )
            currencies = country.get("currencies", {})
            currency_codes = ", ".join(currencies) if isinstance(currencies, dict) else ""

            print(f"Country:    {name}")
            print(f"Capital:    {capital}")
            print(f"Population: {population_text}")
            print(f"Currency:   {currency_codes or 'N/A'}")