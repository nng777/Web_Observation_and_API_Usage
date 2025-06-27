from bs4 import BeautifulSoup
import pandas as pd
import requests
import time

class IndonesianEcommerceScraper:
    def __init__(self):
        self.base_url = "https://www.tokopedia.com/p/"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.products = []

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
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Failed to fetch page {page}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            product_cards = soup.select('div.css-1asz3by')  # You may need to inspect this on the live site

            for card in product_cards:
                name = card.select_one("div.css-1f4mp12").get_text(strip=True) if card.select_one("div.css-1f4mp12") else "-"
                price = card.select_one("div.css-o5uqvq").get_text(strip=True) if card.select_one("div.css-o5uqvq") else "-"
                location = card.select_one("div.css-1kdc32b").get_text(strip=True) if card.select_one("div.css-1kdc32b") else "-"
                self.products.append({
                    "name": name,
                    "price": price,
                    "rating": "-",  # Static HTML doesn't expose rating easily
                    "reviews_count": "-",
                    "category": category,
                    "seller_location": location
                })

            time.sleep(2)  # Be polite

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
