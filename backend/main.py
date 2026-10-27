"""Главный файл backend: сервер FastAPI.

Запуск (из папки backend):
    .venv/bin/uvicorn main:app --reload

После запуска:
    http://localhost:8000          — дашборд
    http://localhost:8000/docs     — автоматическая документация API, там можно «потыкать» запросы
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database
import sensors
from open_meteo import load_real_data

SENSOR_INTERVAL = 3       # секунд между показаниями датчиков
WEATHER_INTERVAL = 10 * 60  # секунд между запросами к Open-Meteo

# Последние данные из Open-Meteo. None — ещё не загрузились или API недоступен
real_data = {"aqi": None, "pm2_5": None, "weather": None, "updated_at": None}


# ===== Фоновые задачи: работают всё время, пока запущен сервер =====

def tick():
    """Один «замер»: новые показания датчиков → в базу."""
    time = database.now()
    readings = sensors.simulate_readings(real_data["aqi"], time)
    database.save_readings(readings)
    database.save_city(sensors.city_summary(readings, real_data["aqi"], time))


async def sensor_loop():
    while True:
        tick()
        await asyncio.sleep(SENSOR_INTERVAL)  # await: пока ждём, сервер отвечает на запросы


async def weather_loop():
    while True:
        try:
            # urllib работает «блокирующе», поэтому запускаем его в отдельном потоке,
            # чтобы сервер не замирал, пока ждёт ответа от Open-Meteo
            real_data.update(await asyncio.to_thread(load_real_data))
            real_data["updated_at"] = database.now()
            print("🌐 Загружены настоящие данные погоды и воздуха")
        except Exception as error:
            # Нет интернета — не падаем, а работаем на симуляции (или на последних данных)
            print("❌ Не удалось загрузить данные из Open-Meteo:", error)
        await asyncio.sleep(WEATHER_INTERVAL)


@asynccontextmanager
async def lifespan(app):
    """Код до yield выполняется при старте сервера, после yield — при остановке."""
    database.init_db()
    weather_task = asyncio.create_task(weather_loop())
    await asyncio.sleep(2)  # даём Open-Meteo пару секунд, чтобы первые замеры были с настоящим AQI
    sensor_task = asyncio.create_task(sensor_loop())
    yield
    weather_task.cancel()
    sensor_task.cancel()


app = FastAPI(title="Smart City API", lifespan=lifespan)


# ===== Наш собственный API =====
# Декоратор @app.get("/адрес") говорит: «когда придёт GET-запрос на этот адрес, вызови функцию».
# То, что функция возвращает (словарь или список), FastAPI сам превращает в JSON.

@app.get("/api/sensors")
def get_sensors():
    """Все датчики на карте с последними показаниями."""
    latest = database.latest_readings()
    result = []
    for sensor in sensors.SENSORS:
        reading = latest.get(sensor["id"])
        result.append({
            "id": sensor["id"],
            "name": sensor["name"],
            "type": sensor["type"],
            "lat": sensor["coords"][0],
            "lon": sensor["coords"][1],
            "unit": sensors.UNITS[sensor["type"]],
            "value": reading["value"] if reading else None,
            "level": reading["level"] if reading else None,
            "status": reading["status"] if reading else None,
            "time": reading["created_at"] if reading else None,
        })
    return result


@app.get("/api/city")
def get_city():
    """Сводка по городу для карточек: значения, уровни, статусы и погода."""
    history = database.city_history(limit=1)
    if not history:
        return {"ready": False}  # сервер только запустился, замеров ещё нет
    last = history[0]

    def card(value, check_result, **extra):
        level, status = check_result
        return {"value": value, "level": level, "status": status, **extra}

    return {
        "ready": True,
        "time": last["created_at"],
        "traffic": card(last["traffic"], sensors.check_traffic(last["traffic"])),
        "air": card(
            last["air"],
            sensors.check_air(last["air"]),
            pm2_5=real_data["pm2_5"],
            source="Open-Meteo" if real_data["aqi"] is not None else "симуляция",
        ),
        "parking": card(
            last["parking"],
            sensors.check_parking(last["parking"], sensors.PARKING_CAPACITY),
            capacity=sensors.PARKING_CAPACITY,
        ),
        "light": card(last["light"], sensors.check_light(last["light"])),
        "weather": real_data["weather"],
        "weather_updated_at": real_data["updated_at"],
    }


@app.get("/api/history")
def get_history(limit: int = Query(20, ge=1, le=500)):
    """История сводок для графика. ?limit=50 — сколько последних точек вернуть (от 1 до 500)."""
    return database.city_history(limit)


# ===== Обращения жителей =====

# Pydantic-модель описывает, какие данные мы ждём от браузера.
# FastAPI сам проверит запрос по этому описанию и, если что-то не так,
# ответит ошибкой 422 с объяснением — наша функция даже не будет вызвана.
# Правило: сервер никогда не доверяет данным из браузера, их легко подделать.
class ReportIn(BaseModel):
    category: Literal["road", "light", "trash", "other"]  # только одно из этих слов
    description: str = Field(min_length=3, max_length=300)
    # Координаты должны быть в районе Алматы, а не где-нибудь в океане
    lat: float = Field(ge=43.0, le=43.5)
    lon: float = Field(ge=76.6, le=77.3)


@app.get("/api/reports")
def get_reports(limit: int = Query(50, ge=1, le=200)):
    """Список обращений: сначала новые, потом решённые."""
    return database.list_reports(limit)


# POST — «создать что-то новое». Данные приходят в теле запроса в виде JSON.
# status_code=201 означает «Created» — стандартный ответ, когда что-то создано.
@app.post("/api/reports", status_code=201)
def create_report(report: ReportIn):
    """Новое обращение жителя."""
    description = report.description.strip()
    if len(description) < 3:
        raise HTTPException(status_code=422, detail="Описание слишком короткое")
    return database.create_report(report.category, description, report.lat, report.lon)


# PATCH — «изменить часть существующего». {report_id} в адресе — это параметр пути:
# запрос на /api/reports/5/resolve вызовет функцию с report_id=5
@app.patch("/api/reports/{report_id}/resolve")
def resolve_report(report_id: int):
    """Отметить обращение решённым."""
    report = database.resolve_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    return report


# Отдаём файлы frontend (index.html, style.css, app.js) по адресу "/".
# Важно: это подключается ПОСЛЕ маршрутов /api, иначе они бы «перекрылись» файлами.
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
