# File: task6_news_scraping.py
from bs4 import BeautifulSoup
import re


class IndonesianNewsScraper:
    def scrape_news_category(self, category):
        """Scrape from: politik, ekonomi, teknologi, olahraga, hiburan"""
        # TODO: Extract title, summary, date, source, category
        # TODO: Collect 100+ articles across 5 categories
        pass

    def clean_news_text(self, text):
        """Clean and preprocess text"""
        pass

    def identify_sentiment_keywords(self):
        """Find positive/negative keywords for preliminary sentiment"""
        pass

# Structure: title, summary, category, source, date, sentiment_keywords