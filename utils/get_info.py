import json
import requests

# Достаем API_KEY из файла 
with open('settings.json', 'r', encoding='utf-8') as file:
    settings = json.load(file)

API_KEY = settings['API_KEY']

# Функция для получения ключа локации по названию города    
def get_location(location):
    try:
        # Отправляем GET-запрос к API AccuWeather
        response = requests.get(
            "https://dataservice.accuweather.com"
            "/locations/v1/cities/translate.json",
            params={
                "apikey": API_KEY,
                "q": location.lower(),
                "language": "ru-ru",
                "details": "true",
            },
        )
        #проверка api
        if response.status_code != 200:
            return 'api_error'
            
        data = response.json()
        if data:
            # Возвращаем ключ локации и локализованное название города
            return (data[0]["Key"], data[0]["LocalizedName"])
        else:
            # На случай если API не вернет данных
            return None

    except Exception as e:
        print(f"Ошибка при получении местоположения: {e}")
        return None

# Функция для получения погоды (форкаст на 5 дней) по ключу локации 
def get_weather_by_location(location_key, location):
    try:
        # Отправляем GET-запрос к API AccuWeather
        response = requests.get(
            "https://dataservice.accuweather.com"
            f"/forecasts/v1/daily/5day/{location_key}",
            params={
                    "apikey": API_KEY,
                    "language": "ru-ru",
                    "details": "true",
                    "metric": "true",
            },
        )
        #проверка api
        if response.status_code != 200:
            return 'api_error'
        
        data = response.json()

        weather = []
        for i, day in enumerate(data['DailyForecasts']):
            # Извлекаем необходимые данные из ответа
            temp = day["Temperature"]["Maximum"]["Value"]
            humidity = day["Day"]["RelativeHumidity"]["Average"]
            wind_speed = day["Day"]["Wind"]["Speed"]["Value"]
            rain_prob = day["Day"]["RainProbability"]

            # Формируем словарь с данными о погоде
            weather_data = {
                "location": location,
                "temperature": temp,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "rain_prob": rain_prob,
                'day': i + 1
            }

            weather.append(weather_data)

        return weather
        
    except Exception as e:
        print(f"Ошибка при получении погоды: {e}")
        return None