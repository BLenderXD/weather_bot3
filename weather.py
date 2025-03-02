import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

OWM_API_KEY = os.getenv("OWM_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Глобальная сессия для переиспользования
_session = None

async def get_session():
    """Ленивая инициализация переиспользуемой сессии."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

async def close_session():
    """Закрытие сессии при завершении работы."""
    global _session
    if _session and not _session.closed:
        await _session.close()

async def fetch_weather_data(city_name: str, session: aiohttp.ClientSession) -> dict:
    """Базовая функция для получения данных о погоде."""
    params = {
        "q": city_name,
        "appid": OWM_API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    try:
        async with session.get(BASE_URL, params=params) as response:
            data = await response.json()
            data["status"] = response.status
            return data
    except Exception as e:
        return {"status": 500, "message": str(e)}

async def check_city_exists(city_name: str) -> tuple[bool, str]:
    """Проверка существования города."""
    session = await get_session()
    data = await fetch_weather_data(city_name, session)

    if data["status"] == 200:
        temp = data["main"]["temp"]
        return True, f"🌆 {city_name} | {temp}°C"
    else:
        msg = data.get("message", "неизвестная ошибка")
        if msg.lower() == "city not found":
            return False, f"🌆 {city_name} | (Город не найден)"
        return False, f"🌆 {city_name} | (ошибка: {msg})"

async def get_weather_label(city_name: str) -> str:
    """Получение краткой метки погоды."""
    success, label = await check_city_exists(city_name)
    return label

async def get_weather_label_parallel(city_names: list[str]) -> list[str]:
    """Параллельное получение меток для списка городов."""
    session = await get_session()
    tasks = [fetch_weather_data(city, session) for city in city_names]
    results = await asyncio.gather(*tasks)

    labels = []
    for city, data in zip(city_names, results):
        if data["status"] == 200:
            temp = data["main"]["temp"]
            labels.append(f"🌆 {city} | {temp}°C")
        else:
            msg = data.get("message", "неизвестная ошибка")
            if msg.lower() == "city not found":
                labels.append(f"🌆 {city} | (Город не найден)")
            else:
                labels.append(f"🌆 {city} | (ошибка: {msg})")
    return labels

async def get_detailed_weather(city_name: str) -> str:
    """Получение подробной информации о погоде (асинхронно)."""
    session = await get_session()
    data = await fetch_weather_data(city_name, session)

    if data["status"] != 200:
        msg = data.get("message", "ошибка")
        if msg.lower() == "city not found":
            return f"🌍 Погода в {city_name} | Город не найден"
        return f"Ошибка детал. погоды: {msg}"

    main = data.get("main", {})
    wind = data.get("wind", {})
    clouds = data.get("clouds", {})
    sys_data = data.get("sys", {})
    weather = data.get("weather", [{}])[0]
    visibility = data.get("visibility", 0)

    temp = main.get("temp")
    feels_like = main.get("feels_like")
    humidity = main.get("humidity")
    pressure = main.get("pressure")
    wind_speed = wind.get("speed")
    wind_deg = wind.get("deg", 0)
    cloudiness = clouds.get("all", 0)
    sunrise_ts = sys_data.get("sunrise")
    sunset_ts = sys_data.get("sunset")
    desc = weather.get("description", "")
    vis_km = visibility / 1000

    now_date = datetime.now().strftime("%d %B %Y")

    def fmt_time(ts):
        return datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "??:??"

    sunrise_str = fmt_time(sunrise_ts)
    sunset_str = fmt_time(sunset_ts)
    direction = get_wind_direction(wind_deg)

    lines = [
        f"<b>🌍 Погода в {city_name} | {now_date}</b>",
        "",
        f"<b>🌡 Температура:</b> {temp}°C <i>(ощущается как {feels_like}°C)</i>",
        f"<b>💧 Влажность:</b> {humidity}%",
        f"<b>📋 Давление:</b> {pressure} гПа",
        f"<b>💨 Ветер:</b> {wind_speed} м/с, {direction}",
        f"<b>☁️ Облачность:</b> {cloudiness}%",
        f"<b>🗒 Описание:</b> {desc}",
        f"<b>👀 Видимость:</b> {vis_km} км",
        f"<b>🌅 Восход:</b> {sunrise_str} | <b>🌇 Закат:</b> {sunset_str}",
    ]
    return "\n".join(lines)




def get_wind_direction(deg: float) -> str:
    """Определение направления ветра (синхронная функция)."""
    dirs = [
        (0, 'северный'), (45, 'северо-восточный'), (90, 'восточный'),
        (135, 'юго-восточный'), (180, 'южный'), (225, 'юго-западный'),
        (270, 'западный'), (315, 'северо-западный'), (360, 'северный')
    ]
    closest = min(dirs, key=lambda x: abs(x[0] - deg))
    return closest[1]