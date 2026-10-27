<div align="center">

# 🏙️ Smart City Dashboard

**Панель мониторинга «умного города» Алматы в реальном времени**

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=flat-square&logo=leaflet&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat-square&logo=chartdotjs&logoColor=white)

![Скриншот дашборда](docs/screenshot.png)

</div>

## О проекте

Backend на Python (FastAPI) собирает показания датчиков города, хранит их в SQLite и отдаёт через свой REST API. Дашборд в браузере каждые 3 секунды берёт с него свежие данные и обновляет карточки, карту и график.

Погода и качество воздуха — **настоящие**, из бесплатного API [Open-Meteo](https://open-meteo.com/). Трафик, парковки и освещение симулируются на сервере.

## ✨ Возможности

| | Модуль | Что показывает |
|---|--------|----------------|
| 🚦 | Трафик | Машин в минуту, предупреждение о пробках |
| 🌫️ | Качество воздуха | Индекс AQI и PM2.5 (Open-Meteo) |
| 🌡️ | Погода | Температура, влажность, ветер (Open-Meteo) |
| 🅿️ | Парковки | Свободные места на трёх парковках |
| 💡 | Освещение | Автоматический ночной и дневной режим |
| 🗺️ | Карта датчиков | 9 датчиков на карте Leaflet с цветом статуса |
| 📈 | История | График последних показаний (Chart.js) |
| 📣 | Обращения жителей | Выбери место на карте, опиши проблему (яма, фонарь, мусор), диспетчер отмечает «Решено» |

Каждый показатель получает статус: 🟢 норма · 🟡 внимание · 🔴 проблема.

## 🏗️ Как это устроено

```mermaid
flowchart LR
    OM[Open-Meteo API] -->|погода и AQI<br/>раз в 10 минут| BE
    SIM[Симуляция датчиков] -->|раз в 3 секунды| BE
    BE[FastAPI backend] <-->|SQL| DB[(SQLite)]
    BE <-->|REST API, JSON| FE[Дашборд в браузере]
```

## 🚀 Как запустить

Нужен Python 3.9 или новее.

```bash
git clone https://github.com/Gadilova/smart-city.git
cd smart-city/backend
python3 -m venv .venv                     # виртуальное окружение (один раз)
.venv/bin/pip install -r requirements.txt # библиотеки (один раз)
.venv/bin/uvicorn main:app --reload       # запуск сервера
```

Потом открой:
- http://localhost:8000 — дашборд
- http://localhost:8000/docs — документация API, где можно отправлять запросы прямо из браузера

Остановить сервер: `Ctrl+C` в терминале.

> Дашборд работает только вместе с backend: если открыть `index.html` напрямую, данных не будет.

## 🔌 API

| Метод и адрес | Что делает |
|---------------|-----------|
| `GET /api/city` | Сводка по городу для карточек и погода |
| `GET /api/sensors` | Все датчики с последними показаниями |
| `GET /api/history?limit=20` | История сводок для графика |
| `GET /api/reports` | Обращения жителей: сначала новые |
| `POST /api/reports` | Создать обращение: `{"category": "road", "description": "...", "lat": 43.24, "lon": 76.93}` |
| `PATCH /api/reports/{id}/resolve` | Отметить обращение решённым |

## 📁 Структура

```
smart-city/
├── backend/
│   ├── main.py            # сервер FastAPI: адреса API и фоновые задачи
│   ├── sensors.py         # датчики, симуляция и правила статусов
│   ├── open_meteo.py      # загрузка настоящей погоды и воздуха
│   ├── database.py        # работа с SQLite (smart_city.db)
│   └── requirements.txt   # библиотеки Python
├── frontend/
│   ├── index.html         # разметка: карточки, карта, обращения, график, журнал
│   ├── style.css          # оформление и цвета статусов
│   └── app.js             # запросы к API и обновление страницы
└── docs/
    └── screenshot.png     # скриншот для README
```

## 🗺️ Планы

- [x] Графики истории (Chart.js)
- [x] Карта города (Leaflet)
- [x] Backend на FastAPI и база данных SQLite
- [x] Frontend берёт данные из backend вместо своей симуляции
- [x] Обращения жителей (POST / PATCH, проверка данных, защита от XSS)
- [ ] Прогноз загруженности дорог с помощью ML
- [ ] Деплой в интернет

---

<div align="center">

Учебный проект · [Aiganym Gadilova](https://github.com/Gadilova)

</div>
