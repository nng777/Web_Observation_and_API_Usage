import json
import threading
import time
from collections import deque
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from tqdm.auto import tqdm


class RealTimeIndonesianDataCollector:
    def __init__(self):
        self.data_buffer = {
            "weather": deque(maxlen=100),
            "news": deque(maxlen=50),
        }
        # shorter default intervals so a demo run quickly gathers some data
        self.update_intervals = {"weather": 30, "news": 60}  # seconds
        self.threads = []
        self.stop_event = threading.Event()

    def start_data_collection(self):
        #Start real-time collection.
        weather_thread = threading.Thread(
            target=self._weather_worker, daemon=True
        )
        #multi-threaded
        news_thread = threading.Thread(target=self._news_worker, daemon=True)
        weather_thread.start()
        news_thread.start()
        self.threads.extend([weather_thread, news_thread])

    def stop(self):
        #Signal worker threads to stop and wait for them to finish.
        self.stop_event.set()
        for t in self.threads:
            t.join(timeout=0)

    def get_current_snapshot(self):
        #Current data state for dashboard
        return {
            "weather": list(self.data_buffer["weather"]),
            "news": list(self.data_buffer["news"]),
        }

    def export_dashboard_data(self):
        #JSON format for dashboard consumption
        snapshot = self.get_current_snapshot()
        metrics = {
            "weather_updates": len(snapshot["weather"]),
            "news_updates": len(snapshot["news"]),
        }
        temps = [
            d.get("temperature_c")
            for d in snapshot["weather"]
            if "temperature_c" in d
        ]
        if temps:
            metrics["avg_temperature_c"] = sum(temps) / len(temps)
        dashboard = {"data": snapshot, "metrics": metrics}
        with open(
            "reports/realtime_dashboard.json", "w", encoding="utf-8"
        ) as f:
            json.dump(dashboard, f, indent=2, ensure_ascii=False)
        return dashboard

    # --------------------------------internal workers----------------------------------
    def _weather_worker(self):
        while not self.stop_event.is_set():
            data = self._fetch_weather()
            if data:
                self.data_buffer["weather"].appendleft(data)
            self.stop_event.wait(self.update_intervals["weather"])

    def _news_worker(self):
        while not self.stop_event.is_set():
            data = self._fetch_news()
            if data:
                self.data_buffer["news"].appendleft(data)
            self.stop_event.wait(self.update_intervals["news"])

    # ----------------------------------Data callers --------------------------------
    def _fetch_weather(self, city="Jakarta"):
        #Fetch current weather for a given city from wttr.in
        url = f"https://wttr.in/{city}?format=j1"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            info = resp.json()["current_condition"][0]
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "city": city,
                "temperature_c": float(info.get("temp_C")),
                "description": info.get("weatherDesc", [{"value": ""}])[0][
                    "value"
                ],
                "humidity": float(info.get("humidity")),
            }
        except Exception as exc:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc),
            }

    def _fetch_news(self):
        #Fetch the latest Indonesian news headline from Google News RSS
        url = "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            item = root.find("channel/item")
            if item is None:
                return None
            title = item.findtext("title")
            link = item.findtext("link")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "title": title,
                "link": link,
            }
        except Exception as exc:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc),
            }


# Structure: real-time weather, news, economic data with timestamps


if __name__ == "__main__":
    collector = RealTimeIndonesianDataCollector()
    collector.start_data_collection()
    runtime = 60
    with tqdm(total=runtime, desc="Collecting", unit="s") as pbar:
        for second in range(runtime):
            time.sleep(1)
            if (second + 1) % 10 == 0:
                collector.export_dashboard_data()
            pbar.update(1)
    collector.stop()