from __future__ import annotations

import os
import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    plt = None  # type: ignore
    PdfPages = None  # type: ignore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0"


def download_html(url: str, path: str, headers: dict[str, str] | None = None) -> str | None:
    """Fetch ``url`` and save the HTML content to ``path``.

    Returns the path to the saved file, or ``None`` on failure.
    """

    if not requests:
        logger.warning("Requests not available; cannot download %s", url)
        return None

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(resp.text)
        return path
    except Exception as exc:  # pragma: no cover - network failures
        logger.warning("Failed to download %s: %s", url, exc)
        return None


def clean_news_text(text: str) -> str:
    """Simple whitespace and punctuation cleanup for sentiment checks."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def identify_sentiment_keywords(text: str) -> dict[str, list[str]]:
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


def _parse_kaskus_html(html: str, max_posts: int) -> list[str]:
    """Extract thread titles from Kaskus search HTML."""

    if not BeautifulSoup:
        return []

    soup = BeautifulSoup(html, "html.parser")
    post_texts: list[str] = []
    selectors = [
        "a.js-thread-title",
        "a.thread-title",
        "div.thread-title a",
        "a[href*='thread']",
    ]
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if text:
                post_texts.append(text)
                if len(post_texts) >= max_posts:
                    break
        if len(post_texts) >= max_posts:
            break

    if not post_texts:
        for tag in soup.find_all("a"):
            text = tag.get_text(strip=True)
            if text:
                post_texts.append(text)
            if len(post_texts) >= max_posts:
                break

    return post_texts[:max_posts]


# ---------------------------------------------------------------------------
# Social Media Sentiment
# ---------------------------------------------------------------------------

def analyze_social_media_sentiment(keyword: str, max_posts: int = 20) -> dict[str, Any]:
    """Scrape Kaskus for threads containing ``keyword`` and analyse sentiment."""

    if not requests or not BeautifulSoup:
        logger.warning(
            "Requests/BeautifulSoup not available; cannot fetch social posts"
        )
        return {"posts": [], "summary": {"positive": 0, "negative": 0}}

    search_url = f"https://www.kaskus.co.id/search?q={requests.utils.quote(keyword)}"
    headers = {"User-Agent": USER_AGENT}
    safe_kw = re.sub(r"\W+", "_", keyword.lower())
    html_file = f"data/kaskus_{safe_kw}.html"

    try:
        saved = download_html(search_url, html_file, headers)
        if not saved:
            return {"posts": [], "summary": {"positive": 0, "negative": 0}}
        with open(saved, encoding="utf-8") as fh:
            html = fh.read()
        post_texts = _parse_kaskus_html(html, max_posts)
    except Exception as exc:
        logger.warning("Failed to fetch posts from kaskus: %s", exc)
        return {"posts": [], "summary": {"positive": 0, "negative": 0}}

    posts = post_texts[:max_posts]
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

    if not requests or not BeautifulSoup:
        logger.warning("Requests/BeautifulSoup not available; cannot fetch weather")
        return None

    slug = city.lower().replace(" ", "-")
    url = f"https://www.timeanddate.com/weather/indonesia/{slug}"
    headers = {"User-Agent": USER_AGENT}
    try:
        html_file = f"data/weather_{slug}.html"
        saved = download_html(url, html_file, headers)
        if not saved:
            return None
        with open(saved, encoding="utf-8") as fh:
            soup = BeautifulSoup(fh, "html.parser")
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


def fetch_upcoming_events(limit: int = 5) -> list[str]:
    """Scrape a few upcoming events from indonesia.travel."""

    if not requests or not BeautifulSoup:
        logger.warning("Requests/BeautifulSoup not available; cannot fetch events")
        return []

    url = "https://indonesia.travel/events/upcoming-event.html"
    try:
        html_file = "data/upcoming_events.html"
        saved = download_html(url, html_file)
        if not saved:
            return []
        with open(saved, encoding="utf-8") as fh:
            soup = BeautifulSoup(fh, "html.parser")
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
) -> list[str]:
    """Search the RedDoorz website for hotels and return hotel titles."""

    if not requests or not BeautifulSoup:
        logger.warning("Requests/BeautifulSoup not available; cannot fetch hotels")
        return []

    url = (
        "https://www.reddoorz.co.id/id-id/list-hotels"
        f"?country=indonesia&city={city_slug}&check_in_date={check_in}"
        f"&check_out_date={check_out}&rooms={rooms}&guest={guests}&sort_by=popular&order_by=desc"
    )
    headers = {"User-Agent": USER_AGENT}
    try:
        html_file = f"data/hotels_{city_slug}.html"
        saved = download_html(url, html_file, headers)
        if not saved:
            return []
        with open(saved, encoding="utf-8") as fh:
            soup = BeautifulSoup(fh, "html.parser")
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
) -> dict[str, Any]:
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
    tourism_data: dict[str, Any],
    sentiment: dict[str, Any],
    path: str = "reports/bonus_report.pdf",
) -> str:
    """Generate a simple PDF report visualising tourism and sentiment data."""

    if not plt or not PdfPages:
        logger.warning("Matplotlib not available; cannot create PDF report")
        return path

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
    if requests and BeautifulSoup and plt:
        sentiment = analyze_social_media_sentiment("Jakarta")
        tourism = generate_tourism_insights(
            city="Jakarta",
            city_slug="cit-jakarta",
            check_in="29-06-2025",
            check_out="30-06-2025",
        )
        create_pdf_report(tourism, sentiment)
        print("Bonus tasks completed")
    else:
        print("Required dependencies are missing; bonus demo skipped")
