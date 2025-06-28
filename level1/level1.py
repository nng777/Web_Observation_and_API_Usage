import requests
from bs4 import BeautifulSoup
import re
import csv


class HTTP_Request:
    @staticmethod
    def get_indonesian_provinces():
        url = "https://www.emsifa.com/api-wilayah-indonesia/api/provinces.json"
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise error if response code is not 200

            provinces = response.json()

            print(f"Total provinces: {len(provinces)}")
            print("First 5 provinces:")
            for province in provinces[:5]:
                print(f"- {province['id']}: {province['name']}")

        except requests.exceptions.RequestException as e:
            print(f"Error occurred during request: {e}")
        pass


class IndonesianCityAPI:
    def __init__(self):
        self.base_url = "https://www.emsifa.com/api-wilayah-indonesia/api"
        self.headers = {"User-Agent": "Mozilla/5.0 (compatible; CityAPI/1.0)"}

    def get_cities_by_province_id(self, province_id):
        #Get cities from a specific province ID
        url = f"{self.base_url}/regencies/{province_id}.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            cities = response.json()
            # print(f"Total cities in province {province_id}: {len(cities)}")
            return cities
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve cities: {e}")
            return []

    def search_city_by_name(self, city_name):
        #Search city by name across all provinces (case-insensitive)
        provinces_url = f"{self.base_url}/provinces.json"
        try:
            provinces = requests.get(
                provinces_url, headers=self.headers
            ).json()
            all_cities = []
            for province in provinces:
                province_id = province["id"]
                cities = self.get_cities_by_province_id(province_id)
                all_cities.extend(cities)

            matched = [
                city
                for city in all_cities
                if city_name.lower() in city["name"].lower()
            ]

            print(f"Cities matching '{city_name}': {len(matched)}")
            for city in matched:
                print(f"- {city['id']}: {city['name']}")

            return matched
        except Exception as e:
            print(f"Error during search: {e}")
            return []


class Web_Scraping:
    def __init__(self):
        self.csv_path = "data/cuaca.csv"

    def scrape_weather_data(self, cities):
        #Fetch weather data for given cities from wttr.in and save to CSV.
        #csv_path = "data/cuaca.csv"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; WeatherScraper/1.0)"
        }
        data = []

        for city in cities:
            slug = city.lower().replace(" ", "-")
            url = f"https://www.timeanddate.com/weather/indonesia/{slug}"
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                qlook = soup.find("div", id="qlook")
                temp_tag = qlook.find("div", class_="h2") if qlook else None
                temperature = (
                    temp_tag.get_text(strip=True).split()[0]
                    if temp_tag
                    else "N/A"
                )
                cond_tag = qlook.find("p") if qlook else None
                condition = (
                    cond_tag.get_text(strip=True) if cond_tag else "N/A"
                )
                humidity = "N/A"
                humid_label = soup.find(string=re.compile("Humidity"))
                if humid_label:
                    humid_td = humid_label.find_next("td")
                    if humid_td:
                        humidity = humid_td.get_text(strip=True).replace(
                            "%", ""
                        )

                print(
                    f"Fetched weather for {city}: {temperature}C, {condition}"
                )

                data.append(
                    {
                        "city": city,
                        "temperature": temperature,
                        "condition": condition,
                        "humidity": humidity,
                    }
                )
            except Exception as exc:
                print(f"Failed to fetch weather for {city}: {exc}")
        if data:
            with open(self.csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=[
                        "city",
                        "temperature",
                        "condition",
                        "humidity",
                    ],
                )
                writer.writeheader()
                writer.writerows(data)

        return data

    def analyze_weather_data(self):
        #Read weather CSV and print basic statistics.
        rows = []
        try:
            with open(self.csv_path, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        row["temperature"] = float(row["temperature"])
                        rows.append(row)
                    except (KeyError, ValueError):
                        pass
        except FileNotFoundError:
            print(f"CSV file not found: {self.csv_path}")
            return None

        if not rows:
            print("No valid weather data to analyze")
            return None

        temps = [r["temperature"] for r in rows]
        highest = max(rows, key=lambda r: r["temperature"])
        lowest = min(rows, key=lambda r: r["temperature"])
        average = sum(temps) / len(temps)

        print("Weather summary:")
        print(
            f"Highest temperature: {highest['city']} {highest['temperature']}C"
        )
        print(f"Lowest temperature: {lowest['city']} {lowest['temperature']}C")
        print(f"Average temperature: {average:.2f}C")

        return {
            "highest": highest,
            "lowest": lowest,
            "average": average,
        }


if __name__ == "__main__":
    HTTP_Request().get_indonesian_provinces()
    print("=========================Complete===========================")
    IndonesianCityAPI().get_cities_by_province_id("32")  # Jawa Barat
    IndonesianCityAPI().search_city_by_name("Bandung")  # Bandung
    print("=========================Complete===========================")
    scraper = Web_Scraping()
    cities = ["Jakarta", "Surabaya", "Bandung", "Medan", "Yogyakarta"]
    scraper.scrape_weather_data(cities)
    scraper.analyze_weather_data()
    print("=========================Complete===========================")