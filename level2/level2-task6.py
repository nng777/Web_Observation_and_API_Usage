import requests
from bs4 import BeautifulSoup
import re
import json
import csv
import time


class IndonesianNewsScraper:
    #Scrape and analyze Indonesian online news.

    def __init__(self):
        # Mapping of category name to starting URL
        self.sources = {
            "internasional": "https://news.detik.com/internasional",
            "ekonomi": "https://finance.detik.com",
            "teknologi": "https://inet.detik.com",
            "olahraga": "https://sport.detik.com",
            "hiburan": "https://hot.detik.com",
        }
        self.headers = {"User-Agent": "Mozilla/5.0"}
        # Grab enough articles
        self.articles_per_category = 20

    def scrape_news_category(self, category):
        #Scrape from: internasional, ekonomi, teknologi, olahraga, hiburan
        url = self.sources.get(category)
        if not url:
            print(f"Unknown category: {category}")
            return []

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
        #Error handling
        except Exception as exc:
            print(f"Failed to fetch {category}: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []

        # Many web pages use <article> tags for listing articles
        cards = soup.select("article")
        for card in cards:
            if len(articles) >= self.articles_per_category:
                break

            title_tag = card.find(["h2", "h3"])
            summary_tag = card.find("p")
            date_tag = card.find("time")

            title = title_tag.get_text(strip=True) if title_tag else ""
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            date = date_tag.get_text(strip=True) if date_tag else ""

            info = {
                "title": self.clean_news_text(title),
                "summary": self.clean_news_text(summary),
                "category": category,
                "source": url,
                "date": date,
            }
            info["sentiment_keywords"] = self.identify_sentiment_keywords(
                info["summary"]
            )
            articles.append(info)

        print(f" Scraped {len(articles)} articles from {category}")
        return articles

    def clean_news_text(self, text):
        #Clean and preprocess text
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", "", text)
        return text.strip()

    def identify_sentiment_keywords(self, text):
        #Find positive/negative keywords for preliminary sentiment
        positive = [
            "akuntabel", "aman", "apresiasi", "baik", "beasiswa", "berhasil", "berkelanjutan",
            "bersih", "cerdas", "canggih", "damai", "demokratis", "setuju", "dukung",
            "efisien", "ekspansi", "hebat", "hijau", "inovatif", "kolaborasi", "kompeten",
            "lestari", "lulus", "maju", "menang", "meningkat", "menguat", "menguntungkan",
            "peduli", "positif", "prestasi", "ramah lingkungan", "reformasi", "responsif",
            "sepakat", "solidaritas", "stabil", "sukses", "terobosan", "transparansi",
            "transformasi", "tumbuh", "unggul"
        ]

        negative = [
            "anjlok", "bencana", "bocor", "buruk", "defisit", "diskriminasi", "ditolak",
            "error", "gagal", "inflasi", "lapar", "keras", "rusak", "timpang", "kalah",
            "mati", "konflik", "korupsi", "krisis", "lemah", "rosot", "miskin",
            "negatif", "parah", "cemar", "langgar", "penurunan", "pengangguran",
            "retas", "pecah", "putus", "rendah", "resesi", "terpinggirkan",
            "tidak lulus", "tidak sah", "tidak stabil", "tidak transparan", "utang"
        ]

        cleaned = self.clean_news_text(text.lower())
        words = cleaned.split()
        return {
            "positive": [w for w in words if w in positive],
            "negative": [w for w in words if w in negative],
        }

    def collect_all_news(self):
        #Scrape all configured categories.
        all_articles = []
        for cat in self.sources:
            articles = self.scrape_news_category(cat)
            all_articles.extend(articles)
            # pause between categories to respect the website
            time.sleep(10)
        return all_articles

    def generate_metrics(self, articles):
        #Summarize article and sentiment counts by category.
        metrics = {}
        for cat in self.sources:
            metrics[cat] = {
                "articles": 0,
                "positive_keywords": 0,
                "negative_keywords": 0,
            }

        for art in articles:
            cat = art.get("category")
            m = metrics.get(cat)
            if m is None:
                continue
            m["articles"] += 1
            m["positive_keywords"] += len(art.get("sentiment_keywords", {}).get("positive", []))
            m["negative_keywords"] += len(art.get("sentiment_keywords", {}).get("negative", []))

        metrics["total_articles"] = len(articles)
        return metrics

    def save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_metrics_csv(self, path, metrics):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["category", "articles", "positive_keywords", "negative_keywords"])
            for cat, m in metrics.items():
                if cat == "total_articles":
                    continue
                writer.writerow([cat, m["articles"], m["positive_keywords"], m["negative_keywords"]])

    def run(self):
        news = self.collect_all_news()
        metrics = self.generate_metrics(news)
        self.save_json("reports/indonesian_news.json", news)
        self.save_metrics_csv("data/indonesian_news_metrics.csv", metrics)
        print(f"Total articles collected: {metrics['total_articles']}")


if __name__ == "__main__":
    scraper = IndonesianNewsScraper()
    scraper.run()