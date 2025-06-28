from __future__ import annotations

import os
import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_news_text(text: str) -> str:
    """Simple whitespace and punctuation cleanup for sentiment checks."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def identify_sentiment_keywords(text: str) -> Dict[str, List[str]]:
    """Identify predefined positive and negative words in the text."""

    positive = [
        "akuntabel",
        "aman",
        "apresiasi",
        "baik",
        "beasiswa",
        "berhasil",
        "berkelanjutan",
        "bersih",
        "cerdas",
        "canggih",
        "damai",
        "demokratis",
        "setuju",
        "dukung",
        "efisien",
        "ekspansi",
        "hebat",
        "hijau",
        "inovatif",
        "kolaborasi",
        "kompeten",
        "lestari",
        "lulus",
        "maju",
        "menang",
        "meningkat",
        "menguat",
        "menguntungkan",
        "peduli",
        "positif",
        "prestasi",
        "ramah lingkungan",
        "reformasi",
        "responsif",
        "sepakat",
        "solidaritas",
        "stabil",
        "sukses",
        "terobosan",
        "transparansi",
        "transformasi",
        "tumbuh",
        "unggul",
    ]
    negative = [
        "anjlok",
        "bencana",
        "bocor",
        "buruk",
        "defisit",
        "diskriminasi",
        "ditolak",
        "error",
        "gagal",
        "inflasi",
        "lapar",
        "keras",
        "rusak",
        "timpang",
        "kalah",
        "mati",
        "konflik",
        "korupsi",
        "krisis",
        "lemah",
        "rosot",
        "miskin",
        "negatif",
        "parah",
        "cemar",
        "langgar",
        "penurunan",
        "pengangguran",
        "retas",
        "pecah",
        "putus",
        "rendah",
        "resesi",
        "terpinggirkan",
        "tidak lulus",
        "tidak sah",
        "tidak stabil",
        "tidak transparan",
        "utang",
    ]

    cleaned = clean_news_text(text.lower())
    words = cleaned.split()
    return {
        "positive": [w for w in words if w in positive],
        "negative": [w for w in words if w in negative],
    }


# ---------------------------------------------------------------------------
# Social Media Sentiment
# ---------------------------------------------------------------------------

def analyze_social_media_sentiment(keyword: str, max_posts: int = 20) -> Dict[str, Any]:
    """Search Social Searcher for posts containing ``keyword``.

    Posts are classified as positive or negative by counting keywords.
    The function returns individual results with detected keywords and an
    overall sentiment summary.
    """

    api_url = (
        "https://www.social-searcher.com/api/v2/search"
        f"?q={requests.utils.quote(keyword)}&lang=id&limit={max_posts}"
    )
    api_key = os.getenv("SOCIAL_SEARCHER_KEY")
    if api_key:
        api_url += f"&key={api_key}"

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch social posts: %s", exc)
        return {"posts": [], "summary": {"positive": 0, "negative": 0}}

    try:
        data = resp.json()
    except Exception as exc:
        logger.warning("Failed to parse social posts JSON: %s", exc)
        return {"posts": [], "summary": {"positive": 0, "negative": 0}}

    posts = [p.get("text", "") for p in data.get("posts", [])]
    sentiments = {"positive": 0, "negative": 0}
    analysed = []

    for text in posts:
        keywords = identify_sentiment_keywords(text)
        pos = len(keywords["positive"])
        neg = len(keywords["negative"])
        if pos > neg:
            label = "positive"
            sentiments["positive"] += 1
        else:
            label = "negative"
            sentiments["negative"] += 1
        analysed.append({
            "text": text,
            "sentiment": label,
            "keywords": keywords,
        })

    logger.info("Fetched %d social posts for '%s'", len(posts), keyword)
    return {"posts": analysed, "summary": sentiments}


# ---------------------------------------------------------------------------
# Tourism Integration
# ---------------------------------------------------------------------------

@dataclass
class WeatherInfo:
    city: str
    temperature: float
    condition: str


def fetch_weather(city: str) -> WeatherInfo | None:
    """Fetch current weather for a city from timeanddate.com."""

    slug = city.lower().replace(" ", "-")
    url = f"https://www.timeanddate.com/weather/indonesia/{slug}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        qlook = soup.find("div", id="qlook")
        temp_tag = qlook.find("div", class_="h2") if qlook else None
        temperature = None
        if temp_tag:
            match = re.search(r"-?\d+(\.\d+)?", temp_tag.get_text(strip=True))
            if match:
                temperature = float(match.group())
        cond_tag = qlook.find("p") if qlook else None
        condition = cond_tag.get_text(strip=True) if cond_tag else ""
        if temperature is None:
            raise ValueError("temperature not found")
        return WeatherInfo(city=city, temperature=temperature, condition=condition)
    except Exception as exc:
        logger.warning("Failed to fetch weather for %s: %s", city, exc)
        return None


def fetch_upcoming_events(limit: int = 5) -> List[str]:
    """Scrape a few upcoming events from indonesia.travel."""

    url = "https://indonesia.travel/events/upcoming-event.html"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".card-event")[:limit]
        return [card.get_text(" ", strip=True) for card in cards]
    except Exception as exc:
        logger.warning("Failed to fetch events: %s", exc)
        return []


def search_hotels(
    city_slug: str,
    check_in: str,
    check_out: str,
    rooms: int = 1,
    guests: int = 2,
) -> List[str]:
    """Search the RedDoorz website for hotels and return hotel titles."""

    url = (
        "https://www.reddoorz.co.id/id-id/list-hotels"
        f"?country=indonesia&city={city_slug}&check_in_date={check_in}"
        f"&check_out_date={check_out}&rooms={rooms}&guest={guests}&sort_by=popular&order_by=desc"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        hotels = [h.get_text(strip=True) for h in soup.select(".hotel-name")]
        return hotels
    except Exception as exc:
        logger.warning("Failed to fetch hotels: %s", exc)
        return []


def generate_tourism_insights(
    city: str,
    city_slug: str,
    check_in: str,
    check_out: str,
    rooms: int = 1,
    guests: int = 2,
) -> Dict[str, Any]:
    """Collect weather, events and hotel data and return combined dict."""

    weather = fetch_weather(city)
    events = fetch_upcoming_events()
    hotels = search_hotels(city_slug, check_in, check_out, rooms, guests)
    return {
        "weather": weather.__dict__ if weather else {},
        "events": events,
        "hotels": hotels,
    }


# ---------------------------------------------------------------------------
# PDF Reporting
# ---------------------------------------------------------------------------

def create_pdf_report(
    tourism_data: Dict[str, Any],
    sentiment: Dict[str, Any],
    path: str = "reports/bonus_report.pdf",
) -> str:
    """Generate a simple PDF report visualising tourism and sentiment data."""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    PdfPages(path).close()  # create/clear file if needed
    with PdfPages(path) as pdf:
        fig, ax = plt.subplots(figsize=(8, 4))
        labels = list(sentiment["summary"].keys())
        sizes = list(sentiment["summary"].values())
        ax.bar(labels, sizes, color=["green", "red"])
        ax.set_ylabel("Posts")
        ax.set_title("Social Media Sentiment")
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        events = tourism_data.get("events", [])
        ax.axis("off")
        text = "\n".join(f"- {e}" for e in events) or "No events"
        ax.text(0, 1, "Upcoming Events:\n" + text, fontsize=12, va="top")
        pdf.savefig(fig)
        plt.close(fig)

    logger.info("Report generated at %s", path)
    return path


if __name__ == "__main__":
    # Example usage demonstrating all bonus features
    sentiment = analyze_social_media_sentiment("Jakarta")
    tourism = generate_tourism_insights(
        city="Jakarta",
        city_slug="cit-jakarta",
        check_in="29-06-2025",
        check_out="30-06-2025",
    )
    create_pdf_report(tourism, sentiment)
    print("Bonus tasks completed")