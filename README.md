# Конфигурация Telegram API (можно переопределить при запуске)
API_ID=24902189
API_HASH=bc628acc3efe8022ca2a906228a810b3
PHONE=+79045995788

# Настройки модели
MODEL_PATH=/app/my_trained_model

# При запуске можно переопределить настройки
docker-compose run -e API_ID=123456 -e API_HASH=your_hash telegram-bot

# Сборка образов
docker-compose build

# Запуск бота (основной сервис)
docker-compose up -d telegram-bot

# Просмотр логов
docker-compose logs -f telegram-bot

# Запуск обучения
docker-compose --profile train up bot-trainer

# Или для фонового режима
docker-compose --profile train up -d bot-trainer
docker-compose --profile train logs -f bot-trainer

# Остановка всех сервисов
docker-compose down

# Перезапуск бота
docker-compose restart telegram-bot

# Запуск shell в контейнере
docker-compose run --rm telegram-bot shell