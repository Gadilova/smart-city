"""Общие настройки для тестов.

Фикстура (fixture) — это подготовка, которую pytest делает перед тестом.
Тест просит её по имени параметра: def test_x(client): ...
"""

import pytest
from fastapi.testclient import TestClient

import database
import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Клиент для запросов к API с отдельной пустой базой.

    tmp_path — временная папка, которую pytest создаёт для каждого теста,
    поэтому тесты не трогают настоящую smart_city.db и не мешают друг другу.
    """
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    # Без "with" TestClient не запускает lifespan: фоновые задачи и запросы
    # в Open-Meteo в тестах не нужны, замеры делаем сами через main.tick()
    return TestClient(main.app)
