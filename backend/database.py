"""Работа с базой данных SQLite.

SQLite — это база данных в одном файле (smart_city.db). Отдельный сервер ей не нужен,
а модуль sqlite3 уже встроен в Python.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

# Файл базы лежит рядом с этим скриптом
DB_PATH = Path(__file__).parent / "smart_city.db"

# Сколько хранить историю: датчики пишут каждые 3 секунды, без чистки база будет расти бесконечно
KEEP_HISTORY = timedelta(days=1)


@contextmanager
def connect():
    """Открывает соединение с базой, сохраняет изменения (commit) и всегда закрывает его."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # строки можно читать по имени колонки: row["value"]
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Создаёт таблицы, если их ещё нет. Таблица — как лист в Excel: колонки и строки."""
    with connect() as conn:
        conn.executescript(
            """
            -- Показания каждого датчика на карте
            CREATE TABLE IF NOT EXISTS readings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id  TEXT NOT NULL,
                value      INTEGER NOT NULL,
                level      TEXT NOT NULL,   -- ok / warn / danger
                status     TEXT NOT NULL,   -- текст статуса, например «Пробка!»
                created_at TEXT NOT NULL
            );

            -- Сводка по всему городу: из неё строится график истории
            CREATE TABLE IF NOT EXISTS city_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                traffic    INTEGER NOT NULL,
                air        INTEGER NOT NULL,
                parking    INTEGER NOT NULL,
                light      INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            -- Обращения жителей: «яма на дороге», «не горит фонарь» и т.п.
            -- Их не удаляем через сутки, как показания: обращения нужно хранить
            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT NOT NULL,
                description TEXT NOT NULL,
                lat         REAL NOT NULL,
                lon         REAL NOT NULL,
                status      TEXT NOT NULL DEFAULT 'new',  -- new (новое) / resolved (решено)
                created_at  TEXT NOT NULL,
                resolved_at TEXT
            );
            """
        )


def now():
    return datetime.now().isoformat(timespec="seconds")


def save_readings(readings):
    """Записывает показания всех датчиков одним запросом и удаляет слишком старые."""
    with connect() as conn:
        # Знаки ? — места для значений. Так безопаснее, чем вклеивать значения в текст SQL
        conn.executemany(
            "INSERT INTO readings (sensor_id, value, level, status, created_at) VALUES (?, ?, ?, ?, ?)",
            [(r["id"], r["value"], r["level"], r["status"], r["time"]) for r in readings],
        )
        cutoff = (datetime.now() - KEEP_HISTORY).isoformat(timespec="seconds")
        conn.execute("DELETE FROM readings WHERE created_at < ?", (cutoff,))
        conn.execute("DELETE FROM city_history WHERE created_at < ?", (cutoff,))


def save_city(summary):
    with connect() as conn:
        conn.execute(
            "INSERT INTO city_history (traffic, air, parking, light, created_at) VALUES (?, ?, ?, ?, ?)",
            (summary["traffic"], summary["air"], summary["parking"], summary["light"], summary["time"]),
        )


def latest_readings():
    """Последнее показание каждого датчика."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT r.* FROM readings r
            JOIN (SELECT sensor_id, MAX(id) AS last_id FROM readings GROUP BY sensor_id) last
              ON r.id = last.last_id
            """
        ).fetchall()
    return {row["sensor_id"]: dict(row) for row in rows}


def create_report(category, description, lat, lon):
    """Сохраняет новое обращение и возвращает его целиком (вместе с id, который выдала база)."""
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO reports (category, description, lat, lon, created_at) VALUES (?, ?, ?, ?, ?)",
            (category, description, lat, lon, now()),
        )
        report_id = cursor.lastrowid  # id новой строки
    return get_report(report_id)


def get_report(report_id):
    """Одно обращение по id или None, если такого нет."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return dict(row) if row else None


def list_reports(limit):
    """Последние обращения: сначала новые, потом решённые; внутри — от свежих к старым."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY status = 'resolved', id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def resolve_report(report_id):
    """Отмечает обращение решённым. Возвращает обновлённое обращение или None, если такого нет."""
    with connect() as conn:
        conn.execute(
            "UPDATE reports SET status = 'resolved', resolved_at = ? WHERE id = ? AND status = 'new'",
            (now(), report_id),
        )
    return get_report(report_id)


def city_history(limit):
    """Последние `limit` сводок по городу, от старых к новым (так удобнее рисовать график)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT traffic, air, parking, light, created_at FROM city_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]
