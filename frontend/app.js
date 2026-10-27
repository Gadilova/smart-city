// Теперь все данные готовит backend (папка backend, сервер FastAPI).
// Задача этого файла — каждые 3 секунды спросить у сервера свежие данные и показать их.
// Симуляция, правила (норма / проблема) и запросы к Open-Meteo переехали в Python.

const REFRESH_INTERVAL = 3000; // как часто спрашиваем сервер, мс
const MAX_POINTS = 20;         // сколько последних точек показывать на графике

// ===== 1. Запросы к нашему API =====

// Загружает адрес нашего backend и возвращает ответ как объект JavaScript.
// Адрес начинается с "/", значит запрос идёт на тот же сервер, с которого открыта страница
async function getJSON(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error("сервер ответил " + response.status);
  }
  return response.json();
}

// ===== 2. Карточки =====

// Пишет число и статус в карточку и красит её рамку.
// card — это кусочек ответа /api/city, например { value: 92, level: "warn", status: "Плотное движение" }
function updateCard(name, card) {
  document.getElementById(name).textContent = card.value;
  document.getElementById(name + "-status").textContent = card.status;

  const element = document.getElementById("card-" + name);
  element.classList.remove("ok", "warn", "danger");
  element.classList.add(card.level);

  // Предупреждения записываем в журнал
  if (card.level === "danger") {
    addLog("⚠️ " + element.querySelector("h2").textContent + ": " + card.status);
  }
}

// "2026-10-28T00:44:38" → "00:44"
function shortTime(isoTime) {
  return isoTime ? isoTime.slice(11, 16) : "--:--";
}

function updateCards(city) {
  updateCard("traffic", city.traffic);
  updateCard("air", city.air);
  updateCard("parking", city.parking);
  updateCard("light", city.light);

  // Вместимость парковок теперь приходит с сервера, а не записана в HTML
  document.getElementById("parking-capacity").textContent = city.parking.capacity;

  const airSource = city.air.source === "Open-Meteo"
    ? "источник: Open-Meteo · PM2.5 " + city.air.pm2_5 + " · " + shortTime(city.weather_updated_at)
    : "источник: симуляция (Open-Meteo недоступен)";
  document.getElementById("air-source").textContent = airSource;

  const weather = city.weather;
  if (weather) {
    document.getElementById("weather").textContent = Math.round(weather.temperature);
    document.getElementById("weather-status").textContent =
      weather.description + " · влажность " + weather.humidity + "% · ветер " + weather.wind_speed + " км/ч";
    document.getElementById("weather-source").textContent = "источник: Open-Meteo · " + shortTime(city.weather_updated_at);
    document.getElementById("card-weather").classList.add("ok");
  } else {
    document.getElementById("weather-status").textContent = "нет данных";
    document.getElementById("weather-source").textContent = "источник: Open-Meteo недоступен";
  }
}

// ===== 3. Журнал событий =====

function addLog(message) {
  const list = document.getElementById("log-list");
  const item = document.createElement("li");
  item.textContent = new Date().toLocaleTimeString("ru-RU") + " — " + message;
  list.prepend(item); // новые события сверху

  // Храним только последние 20 записей
  while (list.children.length > 20) {
    list.lastChild.remove();
  }
}

// ===== 4. График истории (Chart.js) =====

const chart = new Chart(document.getElementById("history-chart"), {
  type: "line",
  data: {
    labels: [], // подписи по оси X: время измерения
    datasets: [
      // Каждый dataset — одна линия на графике
      { label: "🚦 Трафик", data: [], borderColor: "#38bdf8" },
      { label: "🌫️ Воздух (AQI)", data: [], borderColor: "#f97316" },
      { label: "🅿️ Свободные парковки", data: [], borderColor: "#a78bfa" },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false, // высоту берём из .chart-box в CSS
    animation: false,
    elements: { line: { tension: 0.3 }, point: { radius: 2 } }, // сглаженные линии
    scales: {
      x: { ticks: { color: "#94a3b8" }, grid: { color: "#334155" } },
      y: { beginAtZero: true, ticks: { color: "#94a3b8" }, grid: { color: "#334155" } },
    },
    plugins: { legend: { labels: { color: "#e2e8f0" } } },
  },
});

// Историю хранит база данных на сервере, поэтому каждый раз просто заменяем точки целиком.
// Плюс: после перезагрузки страницы график сразу полный, а не начинается с нуля
function updateChart(history) {
  chart.data.labels = history.map((point) => point.created_at.slice(11, 19)); // только время
  chart.data.datasets[0].data = history.map((point) => point.traffic);
  chart.data.datasets[1].data = history.map((point) => point.air);
  chart.data.datasets[2].data = history.map((point) => point.parking);
  chart.update(); // перерисовать график
}

// ===== 5. Карта датчиков (Leaflet) =====

// Цвета кружков: те же, что --ok / --warn / --danger в style.css
const LEVEL_COLORS = { ok: "#22c55e", warn: "#eab308", danger: "#ef4444" };
const TYPE_TITLES = { traffic: "🚦 Трафик", air: "🌫️ Воздух", parking: "🅿️ Парковка" };

// Создаём карту внутри <div id="map">. Центр: Алматы, потом подгоним под датчики
const map = L.map("map").setView([43.238, 76.92], 12);

// Тайлы — это «плитки»-картинки, из которых складывается карта.
// Берём бесплатную карту OpenStreetMap; подпись об авторах обязательна.
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19,
}).addTo(map);

// Кружки на карте по id датчика: { "traffic-1": кружок, ... }
const markers = {};

// Список датчиков и их координаты теперь приходят с сервера (/api/sensors).
// В первый раз создаём кружки, потом только перекрашиваем их
function updateMap(sensors) {
  const isFirstTime = Object.keys(markers).length === 0;

  sensors.forEach((sensor) => {
    if (!markers[sensor.id]) {
      markers[sensor.id] = L.circleMarker([sensor.lat, sensor.lon], {
        radius: 10,
        weight: 2,
        color: "#ffffff",
        fillOpacity: 0.9,
      })
        .bindTooltip(sensor.name) // подсказка при наведении
        .bindPopup("")            // окошко при клике
        .addTo(map);
    }

    const marker = markers[sensor.id];
    if (sensor.value === null) return; // у датчика ещё нет показаний

    marker.setStyle({ fillColor: LEVEL_COLORS[sensor.level] });
    marker.setPopupContent(
      "<b>" + sensor.name + "</b><br>" +
      TYPE_TITLES[sensor.type] + ": " + sensor.value + " " + sensor.unit + "<br>" +
      "Статус: " + sensor.status + "<br>" +
      "<small>замер в " + sensor.time.slice(11, 19) + "</small>"
    );
  });

  // Подгоняем масштаб так, чтобы все датчики поместились на экране (с отступом 30px)
  if (isFirstTime) {
    map.fitBounds(sensors.map((sensor) => [sensor.lat, sensor.lon]), { padding: [30, 30] });
  }
}

// ===== 6. Обновление всей страницы =====

let serverOnline = null; // null — ещё не знаем, true / false — последний результат

async function refresh() {
  try {
    // Promise.all отправляет три запроса одновременно и ждёт все ответы
    const [city, sensors, history] = await Promise.all([
      getJSON("/api/city"),
      getJSON("/api/sensors"),
      getJSON("/api/history?limit=" + MAX_POINTS),
    ]);

    if (serverOnline !== true) {
      addLog("🌐 Подключено к серверу");
      serverOnline = true;
    }

    if (!city.ready) return; // сервер только запустился, первых замеров ещё нет

    updateCards(city);
    updateMap(sensors);
    updateChart(history);
  } catch (error) {
    // Сервер не запущен или упал. Пишем в журнал только один раз, а не каждые 3 секунды
    if (serverOnline !== false) {
      addLog("❌ Нет связи с сервером: " + error.message + ". Запущен ли backend?");
      serverOnline = false;
    }
  }
}

function updateClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString("ru-RU");
}

// ===== 7. Запуск =====
addLog("✅ Система запущена");
updateClock();
setInterval(updateClock, 1000); // часы каждую секунду

refresh();
setInterval(refresh, REFRESH_INTERVAL); // свежие данные с сервера каждые 3 секунды
