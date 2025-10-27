import os
from dotenv import load_dotenv
import sys
import signal
import asyncio
from telethon import TelegramClient, events
import random
import platform
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Загружаем переменные из .env файла
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.append('/app')

# Для лучшей обработки сигналов в Docker
def handle_exit(sig, frame):
    print(f"Received exit signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


class TrainedBot:
    """Бот с обученной моделью"""

    def __init__(self, model_path="./my_trained_model"):
        try:
            self.tokenizer = GPT2Tokenizer.from_pretrained(model_path)
            self.model = GPT2LMHeadModel.from_pretrained(model_path)
            self.model.eval()
            self.model_loaded = True
            print("✅ Обученная модель загружена!")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            self.model_loaded = False
            # Fallback на простые шаблоны
            self.fallback_responses = [
                "Крутой пост! 🔥", "Интересно! 👍", "Отлично! 🚀",
                "Жду еще! 💫", "Супер! 😄"
            ]

    def generate_response(self, post_text):
        if not self.model_loaded:
            return random.choice(self.fallback_responses)

        try:
            # Создаем промпт в том же формате, что и при обучении
            prompt = f"POST: {post_text} RESPONSE:"

            inputs = self.tokenizer.encode(prompt, return_tensors="pt")

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 30,
                    max_new_tokens=25,
                    do_sample=True,
                    temperature=0.8,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_return_sequences=1
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Извлекаем только ответ
            if "RESPONSE:" in response:
                return response.split("RESPONSE:")[-1].strip()
            else:
                return response.replace(prompt, "").strip()

        except Exception as e:
            print(f"⚠️ Ошибка генерации: {e}")
            return random.choice(self.fallback_responses)


async def create_client(session_name):
    """Создает и возвращает клиент Telegram"""
    API_ID = int(os.getenv('API_ID'))
    API_HASH = os.getenv('API_HASH')
    PHONE = os.getenv('PHONE')

    client = TelegramClient(
        session=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        device_model=f'PC-{platform.system()}',
        system_version=platform.release(),
        app_version='4.0.0',
        system_lang_code='ru',
        lang_code='ru'
    )

    await client.start(phone=PHONE)
    print("✅ Авторизация успешна!")
    return client


async def main():
    """Запуск бота с обученной моделью"""
    CHANNELS = {
        '@stepiveter': 'Степиветер',
        '@tracktap': 'Трактэп',
        # '@another_channel': 'Название для логов',
    }

    # 1. Создаем клиент и авторизуемся
    print("🚀 Создание клиента для бота...")
    client = await create_client('bot_session')

    # 2. Загружаем обученную модель
    bot = TrainedBot()

    # Получаем объекты каналов
    channel_entities = []
    successful_channels = {}

    for channel_id, channel_name in CHANNELS.items():
        try:
            entity = await client.get_entity(channel_id)
            channel_entities.append(entity)
            successful_channels[entity.id] = {
                'entity': entity,
                'name': channel_name,
                'id': channel_id
            }
            print(f"✅ Добавлен канал: {channel_name} ({channel_id})")
        except Exception as e:
            print(f"❌ Ошибка получения канала {channel_name} ({channel_id}): {e}")

    if not channel_entities:
        print("❌ Не удалось получить ни одного канала!")
        return

    @client.on(events.NewMessage(chats=channel_entities))
    async def message_handler(event):
        # Получаем информацию о канале
        chat = await event.get_chat()

        # Ищем понятное название канала
        channel_info = successful_channels.get(chat.id, {})
        channel_display_name = channel_info.get('name', chat.title)
        channel_id = channel_info.get('id', 'N/A')

        print(f"📨 Новый пост из [{channel_display_name}]: {event.message.text[:100]}...")

        if event.message.sender_id != (await client.get_me()).id:
            # Используем обученную модель
            post_text = event.message.text or ""
            comment = bot.generate_response(post_text)
            print(f"🤖 Ответ модели для {channel_display_name}: {comment}")

            await asyncio.sleep(random.randint(5, 20))

            try:
                await client.send_message(
                    entity=chat,
                    message=comment,
                    comment_to=event.message.id
                )
                print(f"✅ Комментарий отправлен в [{channel_display_name}]")
            except Exception as e:
                print(f"❌ Ошибка отправки в [{channel_display_name}]: {e}")

    print(f"🚀 Бот с обученной моделью запущен!")
    print(f"📡 Мониторим {len(channel_entities)} каналов:")
    for channel_info in successful_channels.values():
        print(f"   • {channel_info['name']} ({channel_info['id']})")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
