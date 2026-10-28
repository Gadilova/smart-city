"""Датчики города: где стоят, как «измеряют» и как оцениваются показания.

Раньше всё это было в frontend/app.js. Теперь данные создаёт сервер, а браузер только показывает.
"""

import random
from datetime import datetime

# Центр Алматы (широта, долгота)
CITY_CENTER = (43.238, 76.92)

SENSORS = [
    {"id": "traffic-1", "name": "Абая — Достык", "type": "traffic", "coords": (43.238, 76.945)},
    {"id": "traffic-2", "name": "Аль-Фараби — Розыбакиева", "type": "traffic", "coords": (43.212, 76.896)},
    {"id": "traffic-3", "name": "Толе би — Байтурсынова", "type": "traffic", "coords": (43.256, 76.929)},
    {"id": "air-1", "name": "Центр, парк 28 панфиловцев", "type": "air", "coords": (43.259, 76.955)},
    {"id": "air-2", "name": "Алатауский район", "type": "air", "coords": (43.29, 76.84)},
    {"id": "air-3", "name": "Медеу", "type": "air", "coords": (43.157, 77.059)},
    {"id": "parking-1", "name": "Парковка ТРЦ Mega", "type": "parking", "coords": (43.202, 76.892), "capacity": 300},
    {"id": "parking-2", "name": "Парковка Dostyk Plaza", "type": "parking", "coords": (43.233, 76.957), "capacity": 150},
    {"id": "parking-3", "name": "Парковка Зелёный базар", "type": "parking", "coords": (43.264, 76.953), "capacity": 100},
]

PARKING_CAPACITY = sum(s["capacity"] for s in SENSORS if s["type"] == "parking")

UNITS = {"traffic": "машин/мин", "air": "AQI", "parking": "свободных мест"}

# «Типичный день» для трафика: сколько в среднем машин в минуту в каждый час (0..23).
# Утром и вечером часы пик, ночью почти пусто — как в настоящем городе.
TRAFFIC_PROFILE = [
    12, 8, 6, 5, 6, 12,        # 00–05 ночь
    30, 70, 105, 90, 65, 60,   # 06–11 утренний час пик
    65, 60, 58, 62, 75, 98,    # 12–17 день
    110, 92, 70, 50, 35, 20,   # 18–23 вечерний час пик и вечер
]

# Одни перекрёстки загруженнее других: множитель к «типичному дню»
TRAFFIC_LOAD = {"traffic-1": 1.15, "traffic-2": 1.0, "traffic-3": 0.85}


# ===== Правила: те же пороги, что были в app.js =====
# Каждая функция возвращает уровень (ok / warn / danger) и текст статуса.

def check_traffic(value):
    if value > 100:
        return "danger", "Пробка!"
    if value > 70:
        return "warn", "Плотное движение"
    return "ok", "Свободно"


def check_air(value):
    if value > 150:
        return "danger", "Вредно для здоровья"
    if value > 100:
        return "warn", "Умеренно загрязнён"
    return "ok", "Чистый воздух"


def check_parking(free, capacity):
    # Считаем в процентах, потому что у парковок разная вместимость
    share = free / capacity
    if share < 0.05:
        return "danger", "Почти нет мест"
    if share < 0.2:
        return "warn", "Мест мало"
    return "ok", "Места есть"


def check_light(value):
    return "ok", "Ночной режим" if value > 50 else "Дневной режим"


# ===== Симуляция =====

def read_air(real_aqi):
    """Настоящий AQI из API с небольшим разбросом по районам, а без API — случайное число."""
    if real_aqi is None:
        return random.randint(20, 180)
    return max(0, real_aqi + random.randint(-10, 10))


def read_traffic(sensor_id, hour):
    """Трафик по «типичному дню» для этого часа ± случайный разброс 15%."""
    expected = TRAFFIC_PROFILE[hour] * TRAFFIC_LOAD[sensor_id]
    return max(0, round(expected * random.uniform(0.85, 1.15)))


def read_light():
    hour = datetime.now().hour
    is_night = hour < 6 or hour >= 20
    return random.randint(85, 100) if is_night else random.randint(0, 15)


def simulate_readings(real_aqi, time):
    """Новое показание для каждого датчика на карте."""
    readings = []
    hour = datetime.now().hour
    for sensor in SENSORS:
        if sensor["type"] == "traffic":
            value = read_traffic(sensor["id"], hour)
            level, status = check_traffic(value)
        elif sensor["type"] == "air":
            value = read_air(real_aqi)
            level, status = check_air(value)
        else:
            value = random.randint(0, sensor["capacity"])
            level, status = check_parking(value, sensor["capacity"])
        readings.append({"id": sensor["id"], "value": value, "level": level, "status": status, "time": time})
    return readings


def city_summary(readings, real_aqi, time):
    """Сводка по городу из показаний датчиков: средний трафик, воздух, всего свободных мест."""
    by_type = {"traffic": [], "air": [], "parking": []}
    for sensor, reading in zip(SENSORS, readings):
        by_type[sensor["type"]].append(reading["value"])

    return {
        "traffic": round(sum(by_type["traffic"]) / len(by_type["traffic"])),
        # Для города берём настоящий AQI без разброса; если API нет — среднее по датчикам
        "air": real_aqi if real_aqi is not None else round(sum(by_type["air"]) / len(by_type["air"])),
        "parking": sum(by_type["parking"]),
        "light": read_light(),
        "time": time,
    }
