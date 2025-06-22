import requests
import time
import json
import csv


class IndonesianDataCollector:
    def safe_api_call(self, url, max_retries=3, backoff=1):
        """Perform HTTP GET with exponential backoff."""
        delay = backoff
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response
            except Exception:
                if attempt == max_retries - 1:
                    break
                time.sleep(delay)
                delay *= 2
        return None

    def _extract_number_after(self, text, label):
        """Find numeric value appearing after a label."""
        idx = text.find(label)
        if idx == -1:
            return None
        idx += len(label)
        value_chars = []
        while idx < len(text):
            ch = text[idx]
            if ch.isdigit() or ch in '.-':
                value_chars.append(ch)
            elif value_chars:
                break
            idx += 1
        try:
            return float(''.join(value_chars)) if value_chars else None
        except ValueError:
            return None

    def get_regional_data(self):
        """Fetch provinces and their cities."""
        provinces_url = "https://www.emsifa.com/api-wilayah-indonesia/api/provinces.json"
        resp = self.safe_api_call(provinces_url)
        if not resp:
            return []
        provinces = resp.json()
        regions = []
        for prov in provinces:
            pid = prov.get("id")
            cities_url = f"https://www.emsifa.com/api-wilayah-indonesia/api/regencies/{pid}.json"
            c_resp = self.safe_api_call(cities_url)
            cities = c_resp.json() if c_resp else []
            regions.append({
                "province": prov.get("name"),
                "cities": [c.get("name") for c in cities],
            })
        return regions

    def get_economic_indicators(self):
        """Collect GDP growth, inflation, and exchange rate."""
        data = {}

        # Exchange rate (official rate, IDR per USD) from World Bank API
        rate_url = (
            "https://api.worldbank.org/v2/country/IDN/indicator/"
            "PA.NUS.FCRF?format=json"
        )
        rate_resp = self.safe_api_call(rate_url)
        if rate_resp:
            try:
                rate_data = rate_resp.json()[1]
                latest = next(i for i in rate_data if i.get("value") is not None)
                data["exchange_rate_idr_usd"] = float(latest["value"])
            except Exception:
                pass

        # GDP growth (annual %) from World Bank API
        gdp_url = (
            "https://api.worldbank.org/v2/country/IDN/indicator/"
            "NY.GDP.MKTP.KD.ZG?format=json"
        )
        gdp_resp = self.safe_api_call(gdp_url)
        if gdp_resp:
            try:
                gdp_data = gdp_resp.json()[1]
                latest = next(i for i in gdp_data if i.get("value") is not None)
                data["gdp_growth_percent"] = float(latest["value"])
            except Exception:
                pass

        # Inflation rate (consumer prices, annual %) from World Bank API
        infl_url = (
            "https://api.worldbank.org/v2/country/IDN/indicator/"
            "FP.CPI.TOTL.ZG?format=json"
        )
        infl_resp = self.safe_api_call(infl_url)
        if infl_resp:
            try:
                infl_data = infl_resp.json()[1]
                latest = next(i for i in infl_data if i.get("value") is not None)
                data["inflation_yoy_percent"] = float(latest["value"])
            except Exception:
                pass

        return data

    def integrate_all_data(self, json_path = "reports/indonesia_data.json", csv_path = "data/economic_data.csv"):
        """Combine regional and economic data and save to files."""
        regional = self.get_regional_data()
        economic = self.get_economic_indicators()
        combined = {"regions": regional, **economic}

        json_path = "reports/indonesia_data.json"
        csv_path = "data/economic_data.csv"

        with open(json_path, "w") as jf:
            json.dump(combined, jf, indent=2)

        with open(csv_path, "w", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=[
                "exchange_rate_idr_usd",
                "gdp_growth_percent",
                "inflation_yoy_percent",
            ])
            writer.writeheader()
            writer.writerow(economic)
        return combined


if __name__ == "__main__":
    collector = IndonesianDataCollector()
    collector.integrate_all_data()