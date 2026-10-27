"""Загрузка настоящей погоды и качества воздуха из бесплатного API Open-Meteo.

То же самое раньше делал браузер в app.js (fetch). Теперь запрос делает сервер,
а все браузеры получают уже готовый ответ от нашего API.
"""

import json
import urllib.request
from urllib.parse import urlencode

from sensors import CITY_CENTER

COORDS = {"latitude": CITY_CENTER[0], "longitude": CITY_CENTER[1], "timezone": "auto"}

WEATHER_URL = "https://api.open-meteo.com/v1/forecast?" + urlencode(
    {**COORDS, "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"}
)
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality?" + urlencode(
    {**COORDS, "current": "us_aqi,pm2_5"}
)


def fetch_current(url):
    """Отправляет запрос и возвращает часть ответа "current" (как fetchCurrent в app.js)."""
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)["current"]


def weather_text(code):
    """Погодный код WMO → понятный текст."""
    if code == 0:
        return "☀️ Ясно"
    if code <= 3:
        return "⛅ Облачно"
    if code <= 48:
        return "🌫️ Туман"
    if code <= 67:
        return "🌧️ Дождь"
    if code <= 77:
        return "❄️ Снег"
    if code <= 82:
        return "🌦️ Ливень"
    if code <= 86:
        return "🌨️ Снегопад"
    return "⛈️ Гроза"


def load_real_data():
    """Загружает погоду и воздух. Если что-то пошло не так, выбрасывает ошибку — её ловит main.py."""
    weather = fetch_current(WEATHER_URL)
    air = fetch_current(AIR_URL)
    return {
        "aqi": air["us_aqi"],
        "pm2_5": air["pm2_5"],
        "weather": {
            "temperature": weather["temperature_2m"],
            "humidity": weather["relative_humidity_2m"],
            "wind_speed": weather["wind_speed_10m"],
            "description": weather_text(weather["weather_code"]),
        },
    }
