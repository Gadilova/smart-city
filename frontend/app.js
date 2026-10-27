// ===== 1. Симуляция датчиков =====
// Настоящих датчиков у нас пока нет, поэтому генерируем правдоподобные случайные числа.

// Случайное целое число от min до max включительно
function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Читаем показания всех «датчиков» разом
function readSensors() {
  const hour = new Date().getHours();
  const isNight = hour < 6 || hour >= 20;

  return {
    traffic: randomBetween(10, 120),        // машин в минуту
    air: randomBetween(20, 180),            // индекс качества воздуха (AQI)
    parking: randomBetween(0, 200),         // свободных мест
    light: isNight ? randomBetween(85, 100) : randomBetween(0, 15), // % включённых фонарей
  };
}

// ===== 2. Правила: что считать нормой, а что проблемой =====
// Каждая функция возвращает уровень ("ok" / "warn" / "danger") и текст статуса.

function checkTraffic(value) {
  if (value > 100) return { level: "danger", text: "Пробка!" };
  if (value > 70) return { level: "warn", text: "Плотное движение" };
  return { level: "ok", text: "Свободно" };
}

function checkAir(value) {
  if (value > 150) return { level: "danger", text: "Вредно для здоровья" };
  if (value > 100) return { level: "warn", text: "Умеренно загрязнён" };
  return { level: "ok", text: "Чистый воздух" };
}

function checkParking(value) {
  if (value < 10) return { level: "danger", text: "Почти нет мест" };
  if (value < 40) return { level: "warn", text: "Мест мало" };
  return { level: "ok", text: "Места есть" };
}

function checkLight(value) {
  return { level: "ok", text: value > 50 ? "Ночной режим" : "Дневной режим" };
}

// ===== 3. Обновление страницы =====

// Пишет число и статус в карточку и красит её рамку
function updateCard(name, value, result) {
  document.getElementById(name).textContent = value;
  document.getElementById(name + "-status").textContent = result.text;

  const card = document.getElementById("card-" + name);
  card.classList.remove("ok", "warn", "danger");
  card.classList.add(result.level);

  // Предупреждения записываем в журнал
  if (result.level === "danger") {
    addLog("⚠️ " + card.querySelector("h2").textContent + ": " + result.text);
  }
}

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

function refresh() {
  const data = readSensors();
  updateCard("traffic", data.traffic, checkTraffic(data.traffic));
  updateCard("air", data.air, checkAir(data.air));
  updateCard("parking", data.parking, checkParking(data.parking));
  updateCard("light", data.light, checkLight(data.light));
}

function updateClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString("ru-RU");
}

// ===== 4. Запуск =====
addLog("✅ Система запущена");
refresh();
updateClock();
setInterval(refresh, 3000);     // новые данные каждые 3 секунды
setInterval(updateClock, 1000); // часы каждую секунду
