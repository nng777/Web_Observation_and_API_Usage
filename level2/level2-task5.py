from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class IndonesianEcommerceScraper:
    def __init__(self):
        self.base_url = "https://www.tokopedia.com/p/"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.products = []
        self.driver = None

    def _get_driver(self):
        """Initialise Selenium Chrome driver in headless mode."""
        if self.driver:
            return self.driver

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=options
        )
        return self.driver

    def close(self):
        if self.driver:
            self.driver.quit()

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
        driver = self._get_driver()
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}{cat_slug}?page={page}"
            print(f"Scraping: {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div[data-testid='linkProductWrapper']")
                    )
                )
            except Exception:
                print(f"No products found on page {page}")
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            product_cards = soup.select("div[data-testid='linkProductWrapper']")

            for card in product_cards:
                name_el = card.select_one("span[data-testid='spnSRPProdName']")
                price_el = card.select_one("span[data-testid='spnSRPProdPrice']")
                loc_el = card.select_one("span[data-testid='spnSRPShopLoc']")

                name = name_el.get_text(strip=True) if name_el else "-"
                price = price_el.get_text(strip=True) if price_el else "-"
                location = loc_el.get_text(strip=True) if loc_el else "-"

                self.products.append(
                    {
                        "name": name,
                        "price": price,
                        "rating": "-",  # rating not easily available
                        "reviews_count": "-",
                        "category": category,
                        "seller_location": location,
                    }
                )
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
    scraper.close()
