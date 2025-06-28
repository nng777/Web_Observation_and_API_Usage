from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List

from tqdm import tqdm

import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


# ---------------------------------------------------------------------------
# Social media sentiment
# ---------------------------------------------------------------------------

@dataclass
class PostSentiment:
    text: str
    polarity: float
    subjectivity: float


class SocialMediaSentiment:
    """Fetch and analyze social media posts using Social Searcher."""

    def __init__(self) -> None:
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def _download_html(self, url: str, filename: str) -> str:
        """Download a page and save it locally."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
        except Exception:
            return ""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(resp.text)
        return filename

    def fetch_posts(self, query: str, max_results: int = 20) -> List[str]:
        """Scrape public posts for a query from social-searcher.com."""
        url = (
            "https://www.social-searcher.com/social-buzz/"
            f"?q={requests.utils.quote(query)}"
        )
        filename = os.path.join("data", f"social_searcher_{query}.html")
        path = self._download_html(url, filename)
        if not path:
            return []
        with open(path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        posts = [
            p.get_text(" ", strip=True)
            for p in soup.select(
                "div.post-message, div.post-text, div.entry, div.post_content"
            )
        ]
        return posts[:max_results]

    # Backwards compatibility
    def fetch_tweets(self, query: str, max_results: int = 20) -> List[str]:
        """Alias for :meth:`fetch_posts`."""
        return self.fetch_posts(query, max_results)

    def analyze_sentiment(self, posts: Iterable[str]) -> List[PostSentiment]:
        results: List[PostSentiment] = []
        for text in tqdm(posts, desc="Analyzing sentiment", unit="post"):
            blob = TextBlob(text)
            results.append(
                PostSentiment(
                    text=text,
                    polarity=blob.sentiment.polarity,
                    subjectivity=blob.sentiment.subjectivity,
                )
            )
        return results


# ---------------------------------------------------------------------------
# Tourism integration
# ---------------------------------------------------------------------------

@dataclass
class TourismInfo:
    city: str
    weather: Dict[str, str]
    events: List[str]
    hotels: List[str]


class TourismIntegrator:
    """Combine weather, events and hotel data for tourism insights."""

    def __init__(self) -> None:
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_weather(self, city: str) -> Dict[str, str]:
        url = f"https://wttr.in/{requests.utils.quote(city)}?format=j1"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            info = resp.json()["current_condition"][0]
            return {
                "temperature_C": info.get("temp_C"),
                "humidity": info.get("humidity"),
                "description": info.get("weatherDesc", [{"value": ""}])[0]["value"],
            }
        except Exception:
            return {}

    def _download_html(self, url: str, filename: str) -> str:
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
        except Exception:
            return ""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(resp.text)
        return filename

    def fetch_events(self, city: str, limit: int = 5) -> List[str]:
        url = (
            "https://www.traveloka.com/en-id/activities"
            f"?q={requests.utils.quote(city)}"
        )
        filename = os.path.join("data", f"activities_{city}.html")
        path = self._download_html(url, filename)
        if not path:
            return []
        with open(path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        events = [
            e.get_text(" ", strip=True)
            for e in soup.select("h3, div[data-testid='title']")
        ]
        return events[:limit]

    def fetch_hotels(self, city: str, limit: int = 5) -> List[str]:
        url = (
            "https://www.traveloka.com/en-id/hotel"
            f"?q={requests.utils.quote(city)}"
        )
        filename = os.path.join("data", f"hotels_{city}.html")
        path = self._download_html(url, filename)
        if not path:
            return []
        with open(path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        hotels = [
            h.get_text(" ", strip=True)
            for h in soup.select("h3, div[data-testid='title']")
        ]
        return hotels[:limit]

    def integrate_city(self, city: str) -> TourismInfo:
        return TourismInfo(
            city=city,
            weather=self.fetch_weather(city),
            events=self.fetch_events(city),
            hotels=self.fetch_hotels(city),
        )


# ---------------------------------------------------------------------------
# PDF reporting
# ---------------------------------------------------------------------------

class PDFReportGenerator:
    """Generate a simple PDF report from collected data."""

    def create_report(self, infos: List[TourismInfo], path: str = "reports/tourism_report2.pdf") -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with PdfPages(path) as pdf:
            for info in tqdm(infos, desc="Creating PDF", unit="page"):
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.axis("off")
                lines = [
                    f"City: {info.city}",
                    f"Weather: {info.weather.get('temperature_C', 'N/A')}°C, {info.weather.get('description', '')}",
                    f"Events: {', '.join(info.events) if info.events else 'N/A'}",
                    f"Hotels: {', '.join(info.hotels) if info.hotels else 'N/A'}",
                ]
                ax.text(0.02, 0.8, "\n".join(lines), fontsize=10, va="top")
                pdf.savefig(fig)
                plt.close(fig)
        return path


if __name__ == "__main__":
    sentiment = SocialMediaSentiment()
    tweets = sentiment.fetch_tweets("Jakarta")
    results = sentiment.analyze_sentiment(tweets)
    for r in results[:5]:
        print(f"{r.text[:50]}... polarity={r.polarity:.2f}")

    integrator = TourismIntegrator()
    cities = ["Jakarta", "Bandung"]
    data = [
        integrator.integrate_city(city)
        for city in tqdm(cities, desc="Fetching tourism data", unit="city")
    ]
    pdf = PDFReportGenerator().create_report(data)
    print(f"Report saved to {pdf}")