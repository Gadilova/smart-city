"""Тесты API: отправляем запросы, как браузер, и проверяем ответы."""

import database
import main

ALMATY = {"lat": 43.24, "lon": 76.93}


# ===== Данные города =====

def test_city_not_ready_before_first_tick(client):
    assert client.get("/api/city").json() == {"ready": False}


def test_city_and_sensors_after_tick(client):
    main.tick()  # один замер всех датчиков

    city = client.get("/api/city").json()
    assert city["ready"] is True
    assert city["traffic"]["level"] in ("ok", "warn", "danger")
    assert city["parking"]["capacity"] == 550

    sensors = client.get("/api/sensors").json()
    assert len(sensors) == 9
    assert all(s["value"] is not None for s in sensors)


def test_history_limit_is_validated(client):
    assert client.get("/api/history?limit=0").status_code == 422
    assert client.get("/api/history?limit=501").status_code == 422


# ===== Прогноз =====

def test_forecast_uses_typical_day_without_history(client):
    forecast = client.get("/api/forecast?hours=3").json()
    assert len(forecast) == 3
    assert all(item["source"] == "типичный день" for item in forecast)


def test_forecast_switches_to_history(client):
    forecast = client.get("/api/forecast?hours=1").json()
    hour = forecast[0]["hour"]
    for _ in range(20):
        database.add_traffic_sample(hour, 42)

    item = client.get("/api/forecast?hours=1").json()[0]
    assert item["source"] == "история"
    assert item["value"] == 42


def test_forecast_hours_are_validated(client):
    assert client.get("/api/forecast?hours=13").status_code == 422


# ===== Обращения жителей =====

def test_create_and_list_report(client):
    response = client.post("/api/reports", json={"category": "road", "description": "Яма у остановки", **ALMATY})
    assert response.status_code == 201
    report = response.json()
    assert report["status"] == "new"

    reports = client.get("/api/reports").json()
    assert [r["id"] for r in reports] == [report["id"]]


def test_report_validation(client):
    bad_requests = [
        {"category": "ufo", "description": "НЛО над городом", **ALMATY},       # нет такой категории
        {"category": "road", "description": "  a  ", **ALMATY},               # описание из пробелов
        {"category": "road", "description": "Яма", "lat": 0, "lon": 0},       # не в Алматы
    ]
    for body in bad_requests:
        assert client.post("/api/reports", json=body).status_code == 422


def test_resolve_report(client):
    report = client.post("/api/reports", json={"category": "light", "description": "Не горит фонарь", **ALMATY}).json()

    resolved = client.patch(f"/api/reports/{report['id']}/resolve").json()
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None


def test_resolve_missing_report(client):
    assert client.patch("/api/reports/999/resolve").status_code == 404
