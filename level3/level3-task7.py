import sqlite3
import logging
import urllib.request
import json
import schedule
from datetime import datetime
from collections import defaultdict
from pathlib import Path
try:
    from tqdm.auto import tqdm  # type: ignore
except Exception:  # ERROR Handling/ fallback when tqdm progress bar is unavailable
    class _SimpleTqdm:
        def __init__(self, total=0, desc="", unit="step"):
            self.total = total
            self.count = 0
            self.desc = desc

        def __enter__(self):
            print(f"{self.desc} 0/{self.total}", end="", flush=True)
            return self

        def update(self, n=1):
            self.count += n
            print(f"\r{self.desc} {self.count}/{self.total}", end="", flush=True)

        def __exit__(self, exc_type, exc, tb):
            print()

    tqdm = _SimpleTqdm


def fetch_json(url: str):
    #Fetch JSON data from a URL using urllib.
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "indonesia_pipeline.db"
REPORT_PATH = ROOT_DIR / "reports" / "report.html"
LOG_PATH = ROOT_DIR / "data" / "pipeline.log"


class IndonesianDataPipeline:
    def __init__(self):
        self.setup_logging()  # Comprehensive logging
        self.setup_database()  # SQLite tables for weather, news, economic data

    # --------------------------------SETUP----------------------------------

    def setup_logging(self):
        logging.basicConfig(
            filename=LOG_PATH,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    def setup_database(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH))
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                temperature REAL,
                condition TEXT,
                humidity REAL,
                collected_at TEXT
            )
        """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                link TEXT,
                category TEXT,
                collected_at TEXT
            )
        """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS economic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange_rate REAL,
                gdp_growth REAL,
                inflation REAL,
                collected_at TEXT
            )
        """
        )
        self.conn.commit()

    # ----------------------------------Data collectors--------------------------------
    def _collect_weather(self, cities=None):
        if cities is None:
            cities = ["Jakarta", "Surabaya", "Bandung"]
        records = []
        cur = self.conn.cursor()
        for city in cities:
            url = f"https://wttr.in/{city}?format=j1"
            try:
                info = fetch_json(url)["current_condition"][0]
                record = {
                    "city": city,
                    "temperature": float(info.get("temp_C")),
                    "condition": info.get("weatherDesc", [{"value": ""}])[0]["value"],
                    "humidity": float(info.get("humidity")),
                    "collected_at": datetime.utcnow().isoformat(),
                }
                cur.execute(
                    """
                    INSERT INTO weather (city, temperature, condition, humidity, collected_at)
                    VALUES (:city, :temperature, :condition, :humidity, :collected_at)
                """,
                    record,
                )
                records.append(record)
            except Exception as exc:
                logging.warning("Weather fetch failed for %s: %s", city, exc)
        self.conn.commit()
        return records

    def _collect_economic(self):
        url_rate = "https://api.worldbank.org/v2/country/IDN/indicator/PA.NUS.FCRF?format=json"
        url_gdp = "https://api.worldbank.org/v2/country/IDN/indicator/NY.GDP.MKTP.KD.ZG?format=json"
        url_infl = "https://api.worldbank.org/v2/country/IDN/indicator/FP.CPI.TOTL.ZG?format=json"
        record = {"exchange_rate": None, "gdp_growth": None, "inflation": None}
        try:
            r = fetch_json(url_rate)[1]
            record["exchange_rate"] = float(next(i for i in r if i.get("value") is not None)["value"])
        except Exception:
            logging.warning("Failed to fetch exchange rate")
        try:
            r = fetch_json(url_gdp)[1]
            record["gdp_growth"] = float(next(i for i in r if i.get("value") is not None)["value"])
        except Exception:
            logging.warning("Failed to fetch gdp growth")
        try:
            r = fetch_json(url_infl)[1]
            record["inflation"] = float(next(i for i in r if i.get("value") is not None)["value"])
        except Exception:
            logging.warning("Failed to fetch inflation")
        record["collected_at"] = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO economic (exchange_rate, gdp_growth, inflation, collected_at)
            VALUES (:exchange_rate, :gdp_growth, :inflation, :collected_at)
        """,
            record,
        )
        self.conn.commit()
        return record

    def _collect_news(self):
        url = "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id"
        records = []
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                text = resp.read()
            from xml.etree import ElementTree as ET

            root = ET.fromstring(text)
            for item in root.findall("channel/item")[:5]:
                record = {
                    "title": item.findtext("title"),
                    "link": item.findtext("link"),
                    "category": item.findtext("category") or "",
                    "collected_at": datetime.utcnow().isoformat(),
                }
                records.append(record)
        except Exception as exc:
            logging.warning("Failed to fetch news: %s", exc)
            return records

        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT INTO news (title, link, category, collected_at)
            VALUES (:title, :link, :category, :collected_at)
        """,
            records,
        )
        self.conn.commit()
        return records

    def collect_all_data(self):
        #Collect weather, economic, and news data and store in SQLite.
        result = {}
        result["weather"] = self._collect_weather()
        result["economic"] = self._collect_economic()
        result["news"] = self._collect_news()
        return result

    def validate_data_quality(self, data, data_type):
        #Check completeness, format, duplicates.
        metrics = defaultdict(int)
        if isinstance(data, list):
            metrics["records"] = len(data)
            seen = set()
            for item in data:
                tup = tuple(sorted(item.items()))
                if tup in seen:
                    metrics["duplicates"] += 1
                else:
                    seen.add(tup)
                for v in item.values():
                    if v in (None, "", "N/A"):
                        metrics["missing_values"] += 1
        elif isinstance(data, dict):
            metrics["records"] = 1
            metrics["missing_values"] = sum(
                1 for v in data.values() if v in (None, "", "N/A")
            )
        logging.info("%s data quality: %s", data_type, dict(metrics))
        return metrics

    def generate_daily_report(self, metrics):
        #Generate an HTML report showing stored data and quality metrics.
        cur = self.conn.cursor()

        cur.execute("SELECT city, temperature, condition, humidity, collected_at FROM weather")
        weather_rows = cur.fetchall()

        cur.execute("SELECT title, link, category, collected_at FROM news")
        news_rows = cur.fetchall()

        cur.execute("SELECT exchange_rate, gdp_growth, inflation, collected_at FROM economic")
        econ_rows = cur.fetchall()

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        html = [
            "<html><body>",
            f"<h1>Indonesian Data Pipeline Report - {timestamp}</h1>",
            "<h2>Weather</h2>",
            "<table border='1'><tr><th>City</th><th>Temp (C)</th><th>Condition</th><th>Humidity</th><th>Collected</th></tr>",
        ]
        for row in weather_rows:
            html.append(
                f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
            )
        html.append("</table>")
        m = metrics.get("weather", {})
        html.append(
            f"<p><em>Records: {m.get('records', 0)}; Missing Values: {m.get('missing_values', 0)}; Duplicates: {m.get('duplicates', 0)}</em></p>"
        )

        html.append("<h2>News</h2><table border='1'><tr><th>Title</th><th>Link</th><th>Category</th><th>Collected</th></tr>")
        for row in news_rows:
            html.append(
                f"<tr><td>{row[0]}</td><td><a href='{row[1]}'>{row[1]}</a></td><td>{row[2]}</td><td>{row[3]}</td></tr>"
            )
        html.append("</table>")
        m = metrics.get("news", {})
        html.append(
            f"<p><em>Records: {m.get('records', 0)}; Missing Values: {m.get('missing_values', 0)}; Duplicates: {m.get('duplicates', 0)}</em></p>"
        )

        html.append("<h2>Economic</h2><table border='1'><tr><th>Exchange Rate</th><th>GDP Growth</th><th>Inflation</th><th>Collected</th></tr>")
        for row in econ_rows:
            html.append(
                f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
            )
        html.append("</table>")
        m = metrics.get("economic", {})
        html.append(
            f"<p><em>Records: {m.get('records', 0)}; Missing Values: {m.get('missing_values', 0)}; Duplicates: {m.get('duplicates', 0)}</em></p>"
        )

        html.append("</body></html>")
        content = "\n".join(html)

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info("Report generated at %s", REPORT_PATH)
        return str(REPORT_PATH)

    def run_pipeline(self):
        #Run data collection, validation, and report generation once.
        logging.info("Pipeline started")
        try:
            with tqdm(total=3, desc="Pipeline", unit="step") as bar:
                data = self.collect_all_data()
                bar.update(1)
                metrics = {}
                for dtype, records in data.items():
                    metrics[dtype] = self.validate_data_quality(records, dtype)
                bar.update(1)
                self.generate_daily_report(metrics)
                bar.update(1)
            logging.info("Pipeline completed successfully")
        except Exception as exc:
            logging.exception("Pipeline failed: %s", exc)

    def schedule_daily(self, time_str="19:00"):
        #Schedule the pipeline to run every day at the given time(UTC).
        schedule.every().day.at(time_str).do(self.run_pipeline)

    def print_database_contents(self):
        #Print db stored records.
        cur = self.conn.cursor()
        print("Weather:")
        for row in cur.execute("SELECT city, temperature, condition, humidity, collected_at FROM weather"):
            print(row)
        print("News:")
        for row in cur.execute("SELECT title, link, category, collected_at FROM news"):
            print(row)
        print("Economic:")
        for row in cur.execute("SELECT exchange_rate, gdp_growth, inflation, collected_at FROM economic"):
            print(row)


def main():
    #Execute the pipeline once and display stored data.
    pipeline = IndonesianDataPipeline()
    pipeline.run_pipeline()
    pipeline.print_database_contents()
    #pipeline.schedule_daily("06:00")
    #while True:
        #schedule.run_pending()
        #time.sleep(60)

if __name__ == "__main__":
    main()