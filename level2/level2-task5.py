import json
import re
import time
from typing import Any, Dict, List

from bs4 import BeautifulSoup
import pandas as pd
import requests

class IndonesianEcommerceScraper:
    def __init__(self) -> None:
        self.base_url = "https://www.tokopedia.com/p/"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.products: List[Dict[str, Any]] = []

    def close(self) -> None:
        """Placeholder for compatibility with earlier versions."""
        pass

    def _extract_products(self, html: str) -> List[Dict[str, Any]]:
        """Extract product dictionaries from the embedded JSON state."""
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", string=re.compile("window.__STATE__"))
        if script:
            text = script.get_text()
        else:
            text = html

        match = re.search(r"window\.__STATE__\s*=\s*(\{.*?\});", text, re.DOTALL)
        if not match:
            return []

        try:
            state = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

        products: List[Dict[str, Any]] = []

        def _recurse(value: Any) -> None:
            if isinstance(value, dict):
                if value.get("__typename") == "Product" or (
                    "name" in value and "price" in value
                ):
                    products.append(value)
                for v in value.values():
                    _recurse(v)
            elif isinstance(value, list):
                for item in value:
                    _recurse(item)

        _recurse(state)
        return products

    def scrape_products(self, category, max_pages=3):
        """Scrape products: name, price, rating, seller, location"""
        category_map = {
            "elektronik": "handphone-tablet",
            "fashion": "fashion-pria",
            "makanan": "makanan-minuman",
            "rumah-tangga": "rumah-tangga"
        }

        if category not in category_map:
            print(f"Unknown category '{category}'")
            return

        cat_slug = category_map[category]
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}{cat_slug}?page={page}"
            print(f"Scraping: {url}")
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                print(f"Failed to fetch page {page}")
                continue

            products = self._extract_products(resp.text)
            if not products:
                print(f"No products found on page {page}")
                continue

            for item in products:
                self.products.append(
                    {
                        "name": item.get("name", "-"),
                        "price": str(item.get("price", "-")),
                        "rating": item.get("ratingAverage", "-"),
                        "reviews_count": item.get("countReview", "-"),
                        "category": category,
                        "seller_location": item.get("shopCity", "-"),
                    }
                )

            time.sleep(1)  # Be polite

    def analyze_products(self):
        df = pd.DataFrame(self.products)
        if df.empty:
            print("No products to analyze.")
            return

        # Convert price to numeric if possible
        df['price_cleaned'] = df['price'].str.replace(r"[^\d]", "", regex=True).astype(float)

        print("\n=== Average Price per Category ===")
        print(df.groupby("category")["price_cleaned"].mean())

        print("\n=== Top Seller Locations ===")
        print(df["seller_location"].value_counts().head(5))

        print("\n=== Sample Products ===")
        print(df[["name", "price", "seller_location"]].head(10))

        return df


if __name__ == "__main__":
    scraper = IndonesianEcommerceScraper()
    scraper.scrape_products("elektronik", max_pages=2)
    scraper.scrape_products("fashion", max_pages=2)
    df = scraper.analyze_products()
    scraper.close()