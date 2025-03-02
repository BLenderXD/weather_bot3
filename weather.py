import asyncio
import aiohttp
import requests
import datetime

OWM_API_KEY = "3ccc6b2968f4143b92c723a96282e9d8"



async def check_city_exists(city_name: str) -> tuple[bool, str]:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": OWM_API_KEY,
        "units": "metric",
        "lang": "ru"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

                if response.status == 200:
                    temp = data["main"]["temp"]
                    return True, f"🌆 {city_name} | {temp}°C"
                else:
                    msg = data.get("message", "неизвестная ошибка")
                    if msg.lower() == "city not found":
                        return False, f"🌆 {city_name} | (Город не найден)"
                    return False, f"🌆 {city_name} | (ошибка: {msg})"

    except Exception as e:
        return False, f"🌆 {city_name} | (ошибка подключения: {e})"




async def get_weather_label(city_name: str) -> str:
    success, label = await check_city_exists(city_name)  # тоже асинхронная
    return label



async def get_weather_label_parallel(city_names: list[str]) -> list[str]:
    tasks = []
    for city in city_names:
        tasks.append(asyncio.create_task(get_weather_label(city)))
    results = await asyncio.gather(*tasks)
    return results


def get_detailed_weather(city_name: str) -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": OWM_API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if resp.status_code != 200:
            msg = data.get("message", "ошибка")
            if msg.lower() == "city not found":
                return f"🌍 Погода в {city_name} | Город не найден"
            return f"Ошибка детал. погоды: {msg}"

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        sys_data = data.get("sys", {})
        weather = data.get("weather", [{}])[0]

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
        visibility = data.get("visibility", 0)

        now_date = datetime.datetime.now().strftime("%d %B %Y")

        def fmt_time(ts):
            if not ts:
                return "??:??"
            return datetime.datetime.fromtimestamp(ts).strftime("%H:%M")

        sunrise_str = fmt_time(sunrise_ts)
        sunset_str  = fmt_time(sunset_ts)

        direction = get_wind_direction(wind_deg)
        vis_km = visibility / 1000

        lines = []
        lines.append(f"🌍 Погода в {city_name} | {now_date}")
        lines.append("")
        lines.append(f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)")
        lines.append(f"💧 Влажность: {humidity}%")
        lines.append(f"📋 Давление: {pressure} гПа")
        lines.append(f"💨 Ветер: {wind_speed} м/с, {direction}")
        lines.append(f"☁️ Облачность: {cloudiness}%")
        lines.append(f"🗒 Описание: {desc}")
        lines.append(f"👀 Видимость: {vis_km} км")
        lines.append(f"🌅 Восход: {sunrise_str} | 🌇 Закат: {sunset_str}")

        return "\n".join(lines)

    except Exception as e:
        return f"Ошибка детал. погоды (подключение): {e}"

def get_wind_direction(deg: float) -> str:
    dirs = [
        (0, 'северный'),
        (45, 'северо-восточный'),
        (90, 'восточный'),
        (135, 'юго-восточный'),
        (180, 'южный'),
        (225, 'юго-западный'),
        (270, 'западный'),
        (315, 'северо-западный'),
        (360, 'северный')
    ]
    closest = min(dirs, key=lambda x: abs(x[0] - deg))
    return closest[1]
