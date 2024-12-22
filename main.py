import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.get_info import get_location, get_weather_by_location

# Загрузка конфигурации
# Читаем токен бота из JSON-файла настроек для безопасности
with open('settings.json', 'r', encoding='utf-8') as file:
    settings = json.load(file)

# Инициализация базовых компонентов
# Создаем экземпляры бота и диспетчера для обработки сообщений
bot = Bot(token=settings['token'])
dp = Dispatcher()

# Хранилище данных
# Словарь для кэширования последних прогнозов погоды для каждого пользователя
user_weather = {}

# Класс для управления диалогом с пользователем и отслеживания этапов взаимодействия
class WeatherStates(StatesGroup):
    waiting_for_days = State()        # Ожидание выбора количества дней
    waiting_for_start_point = State() # Ожидание ввода начальной точки
    waiting_for_end_point = State()   # Ожидание ввода конечной точки
    waiting_for_intermediate = State() # Ожидание ввода промежуточной точки

# Команда для старта бота, просто приветствие
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для просмотра прогноза погоды.\n"
        "Используйте /weather для получения прогноза. \n"
        "Для получения подробной информации: /help"
    )

# Команда помощи, объясняет что бот умеет делать
@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer(
        "Привет! Данный бот может выдать прогноз погоды на маршруте!\n"
        "Для этого используйте комманду /weather \n"
        "Бот принимает начальную, конечную и промежуточные точки маршрута\n"
        "Выберите период прогноза благодаря инлайн кнопкам: 1/3/5 дней.\n"
        "Через инлайн кнопки вы сможете выбирать день, на который вы смотрите прогноз\n"
        "Если у вас возникли проблемы/вам необходима помощь, обращайтесь: @siberian_cde"
    )

# Основная команда для запроса погоды, начинает весь процесс
@dp.message(Command("weather"))
async def weather_command(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 день", callback_data="days_1"),
            InlineKeyboardButton(text="3 дня", callback_data="days_3"),
            InlineKeyboardButton(text="5 дней", callback_data="days_5")
        ]
    ])
    await message.answer("Выберите период прогноза:", reply_markup=keyboard)
    await state.set_state(WeatherStates.waiting_for_start_point)

# Обработка выбора количества дней для прогноза
@dp.callback_query(lambda c: c.data.startswith("days_"))
async def process_days_selection(callback: types.CallbackQuery, state: FSMContext):
    days = int(callback.data.split("_")[1])
    await state.update_data(days=days)
    await callback.message.answer("Введите начальную точку маршрута:")
    await callback.answer()

# Обработка начальной точки маршрута, которую ввел пользователь
@dp.message(WeatherStates.waiting_for_start_point)
async def process_start_point(message: types.Message, state: FSMContext):
    # Получаем координаты для введенной начальной точки
    # Проверяем доступность API и корректность введенного города
    start_location = get_location(message.text)
    if start_location == 'api_error':
        await message.answer('API недоступно, свяжитесь с разработчиком @...')
        return
    if not start_location:
        await message.answer("Не удалось найти указанный город. Попробуйте еще раз:")
        return
    
    # Сохраняем полученные данные и переходим к следующему этапу
    await state.update_data(start_point=start_location)
    await message.answer("Введите конечную точку маршрута:")
    await state.set_state(WeatherStates.waiting_for_end_point)

# Обработка конечной точки маршрута
@dp.message(WeatherStates.waiting_for_end_point)
async def process_end_point(message: types.Message, state: FSMContext):
    end_location = get_location(message.text)
    if end_location == 'api_error':
        await message.answer('API недоступно, свяжитесь с разработчиком @...')
        return
    if not end_location:
        await message.answer("Не удалось найти указанный город. Попробуйте еще раз:")
        return

    await state.update_data(end_point=end_location)
    
    # Спрашиваем про промежуточные точки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="add_intermediate"),
            InlineKeyboardButton(text="Нет", callback_data="show_forecast")
        ]
    ])
    await message.answer("Хотите добавить промежуточные точки маршрута?", reply_markup=keyboard)

# Добавление промежуточных точек, если юзер захотел
@dp.message(WeatherStates.waiting_for_intermediate)
async def process_intermediate_point(message: types.Message, state: FSMContext):
    intermediate_location = get_location(message.text)
    if intermediate_location == 'api_error':
        await message.answer('API недоступно, свяжитесь с разработчиком @...')
        return
    if not intermediate_location:
        await message.answer("Не удалось найти указанный город. Попробуйте еще раз:")
        return

    data = await state.get_data()
    intermediate_points = data.get('intermediate_points', [])
    intermediate_points.append(intermediate_location)
    await state.update_data(intermediate_points=intermediate_points)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Добавить еще", callback_data="add_intermediate"),
            InlineKeyboardButton(text="Показать прогноз", callback_data="show_forecast")
        ]
    ])
    await message.answer(f"Точка {intermediate_location[1]} добавлена! Хотите добавить еще одну промежуточную точку?", 
                        reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "add_intermediate")
async def add_intermediate_point(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите промежуточную точку маршрута:")
    await state.set_state(WeatherStates.waiting_for_intermediate)
    await callback.answer()

#Отображение погоды на всем маршруте по дням
@dp.callback_query(lambda c: c.data == "show_forecast")
async def show_forecast(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Получаем сохраненные данные о маршруте
        data = await state.get_data()
        print(f"Debug - State data: {data}")  # Отладочная информация
        
        # Проверка наличия необходимых данных
        if not data:
            await callback.message.answer("Нет данных. Пожалуйста, начните заново с команды /weather")
            await callback.answer()
            return
            
        # Извлекаем основные параметры маршрута
        start_location = data.get('start_point')
        end_location = data.get('end_point')
        days = data.get('days')
        
        # Проверка полноты данных
        if not all([start_location, end_location, days]):
            await callback.message.answer("Недостаточно данных. Пожалуйста, начните заново с команды /weather")
            await callback.answer()
            return
            
        # Формируем полный маршрут с учетом промежуточных точек
        intermediate_points = data.get('intermediate_points', [])
        all_points = [start_location] + intermediate_points + [end_location]
        
        # Получаем прогноз для всех точек
        all_weather = []

        for point in all_points:
            weather = get_weather_by_location(point[0], point[1])
            if weather == 'api_error':
                await callback.answer('API недоступно, свяжитесь с разработчиком @...')
                return

            if not weather:
                await callback.message.answer(f"Ошибка при получении прогноза для города {point[1]}")
                await state.clear()
                return
            all_weather.append((point[1], weather))

        # Сохраняем данные пользователя
        user_id = callback.from_user.id
        user_weather[user_id] = {
            'days': days,
            'locations': all_weather
        }

        # Показываем прогноз
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"{'✅' if i == 1 else ''} День {i}",
                callback_data=f"day_{i}"
            ) for i in range(1, days + 1)
        ]])

        weather_text = f"🗺 Прогноз погоды на {days} {'день' if days == 1 else 'дня' if days < 5 else 'дней'}:\n\n"
        weather_text += f"📅 День 1:\n\n"

        for city, weather in all_weather:
            weather_text += f"🏁 {city}:\n"
            weather_text += f"🌡 Температура: {weather[0]['temperature']}°C\n"
            weather_text += f"💧 Влажность: {weather[0]['humidity']}%\n"
            weather_text += f"💨 Ветер: {weather[0]['wind_speed']} км/ч\n"
            weather_text += f"☔️ Вероятность дождя: {weather[0]['rain_prob']}%\n\n"

        await callback.message.answer(weather_text, reply_markup=keyboard)
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        # Полная отладочная информация об ошибке
        print(f"Debug - Full error in show_forecast: {str(e)}") 
        await callback.message.answer("Произошла ошибка. Попробуйте запросить прогноз заново через /weather")
        await callback.answer()
        await state.clear()

# Переключение между днями прогноза через кнопки
@dp.callback_query(lambda c: c.data.startswith("day_"))
async def switch_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_weather:
        await callback.message.answer("Данные устарели. Запросите прогноз заново через /weather")
        await callback.answer()
        return

    try:
        day = int(callback.data.split("_")[1])
        data = user_weather[user_id]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"{'✅' if i == day else ''} День {i}",
                callback_data=f"day_{i}"
            ) for i in range(1, data['days'] + 1)
        ]])

        weather_text = f"🗺 Прогноз погоды на {data['days']} {'день' if data['days'] == 1 else 'дня' if data['days'] < 5 else 'дней'}:\n\n"
        weather_text += f"📅 День {day}:\n\n"

        for city, weather in data['locations']:
            weather_text += f"🏁 {city}:\n"
            weather_text += f"🌡 Температура: {weather[day-1]['temperature']}°C\n"
            weather_text += f"💧 Влажность: {weather[day-1]['humidity']}%\n"
            weather_text += f"💨 Ветер: {weather[day-1]['wind_speed']} км/ч\n"
            weather_text += f"☔️ Вероятность дождя: {weather[day-1]['rain_prob']}%\n\n"

        await callback.message.edit_text(weather_text, reply_markup=keyboard)
    except Exception as e:
        print(f"Error in switch_day: {e}")
        await callback.message.answer("Произошла ошибка. Запросите прогноз заново через /weather")
    
    await callback.answer()

# Функция для красивого вывода погоды за конкретный день
async def show_weather_day(message: types.Message, day: int):
    user_id = message.from_user.id
    data = user_weather[user_id]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"{'✅' if i == day else ''} День {i}",
            callback_data=f"day_{i}"
        ) for i in range(1, data['days'] + 1)
    ]])

    weather_text = f"🗺 Прогноз погоды на {data['days']} {'день' if data['days'] == 1 else 'дня' if data['days'] < 5 else 'дней'}:\n\n"
    weather_text += f"📅 День {day}:\n\n"

    for city, weather in data['locations']:
        weather_text += f"🏁 {city}:\n"
        weather_text += f"🌡 Температура: {weather[day-1]['temperature']}°C\n"
        weather_text += f"💧 Влажность: {weather[day-1]['humidity']}%\n"
        weather_text += f"💨 Ветер: {weather[day-1]['wind_speed']} км/ч\n"
        weather_text += f"☔️ Вероятность дождя: {weather[day-1]['rain_prob']}%\n\n"

    await message.answer(weather_text, reply_markup=keyboard)

async def main():
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Точка входа в программу
    # Запуск асинхронного цикла обработки событий
    asyncio.run(main())