"""Тесты правил: какое значение считается нормой, а какое — проблемой."""

import sensors


def test_check_traffic():
    assert sensors.check_traffic(50)[0] == "ok"
    assert sensors.check_traffic(80)[0] == "warn"
    assert sensors.check_traffic(120)[0] == "danger"


def test_check_air():
    assert sensors.check_air(40)[0] == "ok"
    assert sensors.check_air(120)[0] == "warn"
    assert sensors.check_air(200)[0] == "danger"


def test_check_parking_uses_share_of_capacity():
    # 10 свободных мест — много для маленькой парковки и мало для большой
    assert sensors.check_parking(10, 40)[0] == "ok"
    assert sensors.check_parking(10, 100)[0] == "warn"
    assert sensors.check_parking(10, 300)[0] == "danger"


def test_traffic_profile_has_rush_hours():
    profile = sensors.TRAFFIC_PROFILE
    assert len(profile) == 24
    assert profile[8] > profile[3] * 5   # утром в час пик намного больше, чем ночью
    assert profile[18] == max(profile)   # вечерний час пик — самый загруженный


def test_read_traffic_stays_near_profile():
    for _ in range(100):
        value = sensors.read_traffic("traffic-2", 8)
        assert 0.85 * 105 - 1 <= value <= 1.15 * 105 + 1
