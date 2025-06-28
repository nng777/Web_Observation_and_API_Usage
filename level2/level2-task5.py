import requests
import pandas as pd
from bs4 import BeautifulSoup
import time


class FakeStoreHTMLScraper:
    def __init__(self):
        self.base_url = "https://fakestoreapi.com/products"
        self.html_file = "data/fakestore_mock.html"
        self.products = []

    def fetch_and_save_html(self):
        #Fetch JSON from FakeStoreAPI and save mock HTML to file
        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()
            products = response.json()
        except Exception as e:
            print(f" Failed to fetch API: {e}")
            return

        # Simulate an HTML page
        html = "<html><body><div class='products'>"
        for p in products:
            html += f"""
            <div class='product'>
                <h2 class='title'>{p['title']}</h2>
                <span class='price'>{p['price']}</span>
                <span class='category'>{p['category']}</span>
            </div>
            """
        html += "</div></body></html>"

        # Save to file
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f" Mock HTML saved to {self.html_file}")
        time.sleep(2)

    def parse_html_and_extract(self):
        #Use BeautifulSoup to parse the HTML and extract product info
        try:
            with open(self.html_file, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
        except Exception as e:
            print(f" Failed to read HTML file: {e}")
            return

        product_divs = soup.select(".product")

        for div in product_divs:
            title = div.select_one(".title").text.strip()
            price = float(div.select_one(".price").text.strip())
            category = div.select_one(".category").text.strip()
            self.products.append({
                "title": title,
                "price": price,
                "category": category
            })

        print(f" Extracted {len(self.products)} products from HTML")

    def analyze_products(self):
        if not self.products:
            print(" No products to analyze.")
            return

        df = pd.DataFrame(self.products)

        print("\n Average Price per Category")
        print(df.groupby("category")["price"].mean())

        print("\n Sample Products")
        print(df[["title", "price", "category"]].head(10))

        df.to_csv("data/fakestore_bs_products.csv", index=False)
        print("\n Saved to fakestore_bs_products.csv")

        return df


if __name__ == "__main__":
    scraper = FakeStoreHTMLScraper()
    scraper.fetch_and_save_html()
    scraper.parse_html_and_extract()
    df = scraper.analyze_products()
