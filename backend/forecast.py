"""Прогноз трафика на ближайшие часы.

Идея «сезонного прогноза» (seasonal naive): трафик каждый день повторяется по часам —
в 8 утра пробки, в 3 ночи пусто. Значит, лучшая простая догадка про 18:00 —
это средний трафик, который мы уже видели в 18:00 раньше.

Это базовая модель из машинного обучения для временных рядов: с ней сравнивают
более сложные модели. Если сложная модель не лучше — она не нужна.
"""

from datetime import datetime, timedelta

import database
import sensors

# Сколько замеров за час нужно, чтобы доверять истории. Датчики пишут каждые 3 секунды,
# так что 20 замеров — это одна минута наблюдений за этот час
MIN_SAMPLES = 20


def traffic_forecast(hours):
    """Прогноз на `hours` часов вперёд: список {time, hour, value, level, status, source}."""
    learned = database.traffic_by_hour()
    start = datetime.now().replace(minute=0, second=0, microsecond=0)

    result = []
    for step in range(1, hours + 1):
        time = start + timedelta(hours=step)
        average, samples = learned.get(time.hour, (None, 0))

        if samples >= MIN_SAMPLES:
            value, source = round(average), "история"
        else:
            # Этот час мы ещё не наблюдали — берём «типичный день» (знание заранее)
            value, source = sensors.TRAFFIC_PROFILE[time.hour], "типичный день"

        level, status = sensors.check_traffic(value)
        result.append({
            "time": time.isoformat(timespec="minutes"),
            "hour": time.hour,
            "value": value,
            "level": level,
            "status": status,
            "source": source,
            "samples": samples,
        })
    return result
