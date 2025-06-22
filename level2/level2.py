import requests
import json
import time
import os
from bs4 import BeautifulSoup
import re

class IndonesianDataCollector:
    def __init__(self, max_retries=3, backoff=1):
        self.max_retries = max_retries
        self.backoff = backoff

    def safe_get(self, url, headers=None, expect_json=False):
        delay = self.backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=20)
                response.raise_for_status()
                return response.json() if expect_json else response.text
            except Exception as e:
                print(f"[{url}] Attempt {attempt+1} failed: {e}")
                time.sleep(delay)
                delay *= 2
        print(f"❌ Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def get_exchange_rate(self):
        print("Fetching exchange rate...")
        url = "https://api.exchangerate.host/latest?base=USD&symbols=IDR"
        data = self.safe_get(url, expect_json=True)
        if data and "rates" in data and "IDR" in data["rates"]:
            return {"Exchange Rate (IDR/USD)": data["rates"]["IDR"]}
        print("Exchange rate fetch error. Raw data:", data)
        return {}

    def get_inflation_and_gdp(self):
        print("Fetching inflation and GDP...")
        url = "https://tradingeconomics.com/indonesia"
        headers = {"User-Agent": "Mozilla/5.0"}
        html = self.safe_get(url, headers=headers)
        result = {}

        if html:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text()

            # Try flexible inflation regex
            inflation_match = re.search(r"Inflation Rate[^0-9]*([\d.]+)", text, re.IGNORECASE)
            if inflation_match:
                result["Inflation Rate (YoY %)"] = float(inflation_match.group(1))
            else:
                print("Inflation not found")

            # Try flexible GDP growth regex
            gdp_match = re.search(r"GDP Growth Rate[^0-9]*([\d.]+)", text, re.IGNORECASE)
            if gdp_match:
                result["GDP Growth (annual %)"] = float(gdp_match.group(1))
            else:
                print("GDP Growth not found")

        return result

    def integrate_all(self):
        exchange_data = self.get_exchange_rate()
        economic_data = self.get_inflation_and_gdp()

        all_data = {}
        all_data.update(exchange_data)
        all_data.update(economic_data)

        os.makedirs("output", exist_ok=True)
        with open("output/combined_data.json", "w") as f:
            json.dump(all_data, f, indent=2)

        print("✅ Data saved to output/combined_data.json")


if __name__ == "__main__":
    collector = IndonesianDataCollector()
    collector.integrate_all()
