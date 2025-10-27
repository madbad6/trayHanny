#!/bin/bash

set -e

echo "🚀 Starting Telegram Bot Container"

# Функция для запуска бота
run_bot() {
    echo "🤖 Starting Telegram Bot..."
    if [ ! -d "/app/my_trained_model" ] || [ -z "$(ls -A /app/my_trained_model)" ]; then
        echo "⚠️  No trained model found. Please train the model first or mount the model directory."
        echo "📚 To train the model, run: docker-compose --profile train up bot-trainer"
        exit 1
    fi

    python run_bot.py
}

# Функция для обучения модели
train_model() {
    echo "🎯 Starting Model Training..."

    # Проверяем наличие сессии
    if [ ! -f "/app/sessions/data_collector_session.session" ]; then
        echo "📱 No session file found. Starting initial authentication..."
        python -c "
import asyncio
from train_bot import create_client
asyncio.run(create_client('data_collector_session'))
"
    fi

    python train_bot.py
}

# Обработка команд
case "$1" in
    "run")
        run_bot
        ;;
    "train")
        train_model
        ;;
    "shell")
        exec /bin/bash
        ;;
    *)
        echo "Usage: $0 {run|train|shell}"
        echo "  run   - Run the Telegram bot"
        echo "  train - Train the model"
        echo "  shell - Open shell in container"
        exit 1
        ;;
esac