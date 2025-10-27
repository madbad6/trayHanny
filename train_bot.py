from telethon import TelegramClient, events
import asyncio
import random
import platform
import json
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import Dataset
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sys
import signal
import asyncio

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

class DataCollector:
    """Сборщик данных из канала"""

    def __init__(self):
        self.posts_data = []

    async def collect_posts(self, client, channel_username, limit=10000):
        """Собираем посты из канала используя переданный клиент"""
        print(f"📊 Собираю посты из: {channel_username}")

        channel = await client.get_entity(channel_username)
        print(f"📊 Найден канал: {channel.title}")

        # Собираем посты
        posts = []
        total_collected = 0

        try:
            # Пробуем собрать за последние 180 дней
            since_date = datetime.now() - timedelta(days=730)
            async for message in client.iter_messages(
                    channel,
                    limit=limit,
                    offset_date=since_date
            ):
                if message.text and len(message.text.strip()) > 5:  # Уменьшил до 5 символов
                    posts.append(message.text)
                    total_collected += 1
                    if total_collected % 50 == 0:
                        print(f"📝 Собрано {total_collected} постов...")

        except Exception as e:
            print(f"⚠️ Ошибка при сборе с датой: {e}")
            # Если не получилось с датой, собираем просто по лимиту
            async for message in client.iter_messages(channel, limit=limit):
                if message.text and len(message.text.strip()) > 5:
                    posts.append(message.text)
                    total_collected += 1
                    if total_collected % 50 == 0:
                        print(f"📝 Собрано {total_collected} постов...")

        print(f"✅ Всего собрано {len(posts)} постов")
        return posts


class ResponseGenerator:
    """Генератор ответов для обучения"""

    def generate_responses(self, posts):
        """Генерируем крутые ответы на посты"""
        responses = []

        for i, post in enumerate(posts):
            post_lower = post.lower()

            # Генерация ответов в стиле крафтовой культуры с юмором
            if any(word in post_lower for word in
                   ['пиво', 'beer', 'пенный', 'лагер', 'эль', 'стаут', 'ipa', 'apa', 'крафт']):
                response = random.choice([
                    "Отличный крафт! Хмель просто бомба! 🍺🔥",
                    "Пиво, от которого мурашки по коже! 🍻✨",
                    "Такой эль можно пить литрами! 😍🍺",
                    "Настоящий крафт - чувствуется рука мастера! 👨🍻",
                    "Пиво, ради которого стоит жить! 🍺💫",
                    "Хмельная феерия! Жду продолжения! 🎉🍻",
                    "Этот стаут - просто космос! 🌌🍺",
                    "Этот IPA настолько горький, что даже парень одобрил! 😂🍺",
                    "Говорят, после этого стаута можно увидеть звук и услышать цвет. Проверим? 🌈🍺",
                    "Крафт, от которого у бороды самой начинает расти хмель! 🧔‍♀️🍺",
                    "Это не пиво, это хмельная терапия от всех жизненных проблем. 🛀🍺",
                    "Такое пиво, что даже лосось бы пошёл на нерест в твой бокал! 🐟🍺",
                    "После этого пива понимаешь, что 'apa' - это не опечатка, а крик души! 🗣️🍺",
                    "Пенный, как мои мысли о завтрашнем дне по понедельникам. 😵"
                ])
            elif any(word in post_lower for word in ['мед', 'мёд', 'пчел', 'пчёлы', 'медовух', 'мид', 'mead']):
                response = random.choice([
                    "Медовуха - напиток богов! 🍯👑",
                    "Настоящий мид - слаще поцелуя! 💋🍯",
                    "Пчелки бы одобрили! 🐝❤️",
                    "Мед, от которого душа поет! 🎵🍯",
                    "Золотой напиток для золотых людей! ✨🍯",
                    "Медовуха, которая греет душу! 🔥🍯",
                    "Настоящая медовая магия! 🧙🍯",
                    "Эта медовуха настолько сладкая, что у инсулина слюнки потекли! 🍯😆",
                    "Пчёлы, которые это сделали, наверное, получили Нобелевскую премию по гастрономии. 🐝🏆",
                    "После этого мида начинаешь понимать язык пчёл. Ж-ж-ж-желаю ещё! 🐝🗣️",
                    "Мёд, от которого Винни-Пух продал бы душу. И ещё попросил добавки. 🐻💸",
                    "Это не опьянение, это состояние 'медового блаженства'. Осторожно, вызывает привыкание! 🍯😵",
                    "Настоящий мид - когда понимаешь, что 'пчелиный труд' - это не метафора! 🐝💪"
                ])
            elif any(word in post_lower for word in ['сидр', 'cider', 'яблочн', 'груш']):
                response = random.choice([
                    "Сидр - осень в бокале! 🍂🍎",
                    "Яблочная свежесть - что может быть лучше! 🍏✨",
                    "Сидр, от которого щеки розовеют! 🍎😊",
                    "Настоящий яблочный восторг! 🍎🎉",
                    "Сидр для истинных ценителей! 👌🍎",
                    "Пахнет яблоками и счастьем! 🍎💫",
                    "Освежающий как утренняя роса! 🌅🍎",
                    "Этот сидр настолько яблочный, что Ньютон под ним не только яблоко поймал, но и теорию относительности допил! 🍎🔭",
                    "Сидр, от которого даже Гренни Смит покраснела бы! 🍏😳",
                    "После этого сидра начинаешь видеть core-плоды, а не обычные яблоки! 🍎💻",
                    "Освежающий, как пощечина снежной королевы. Но приятнее! ❄️🍎",
                    "Грушевый сидр? Это когда ты такой элегантный, что даже пьянеешь с акцентом. 🍐🎩"
                ])
            elif any(word in post_lower for word in ['вино', 'виноград', 'винн', 'шампанск', 'игристое']):
                response = random.choice([
                    "Вино, от которого кружится голова! 🍷😵",
                    "Букет просто божественный! 👃🍷",
                    "Вино для романтических вечеров! 🌹🍷",
                    "Настоящая виноградная поэзия! 📖🍇",
                    "Игристое, как новогодняя ночь! 🎆🥂",
                    "Вино, которое рассказывает историю! 🗣️🍷",
                    "Бокал вина - лекарство от всего! 💊🍷",
                    "Букет у вина такой сложный, что для его описания нужно высшее филологическое образование! 🍷📚",
                    "Это вино настолько выдержанное, что оно помнит, как Наполеон был ещё лейтенантом! 🍷👴",
                    "После этого шампанского понимаешь, что 'игристое' - это не про вино, а про твоё настроение! 🥂✨",
                    "Вино, от которого даже сомелье заплакал и позвонил маме. 🍷😭📞",
                    "Таннины такие бархатные, что хочется пошить из них пиджак. 🍷🧥"
                ])
            elif any(word in post_lower for word in ['алкогол', 'виски', 'водка', 'коньяк', 'ром', 'джин', 'текила']):
                response = random.choice([
                    "Крепкий напиток для сильных духом! 💪🥃",
                    "Алкоголь, который лечит душу! ❤️🩹",
                    "На таком и горы свернешь! 🏔️🥃",
                    "Напиток настоящих ценителей! 👑🥃",
                    "Крепость, которая согреет изнутри! 🔥🥃",
                    "Алкоголь - искусство в жидком виде! 🎨🥃",
                    "Для смелых и решительных! 🥷🥃",
                    "Этот виски настолько выдержанный, что у него уже есть ипотека и два ребёнка в колледже. 🥃🏠",
                    "После этого рома начинаешь понимать, о чём пел пират в той песне. Йо-хо-хо и бутылка... 🏴‍☠️🥃",
                    "Водка настолько чистая, что через неё можно рассматривать свои жизненные ошибки. 🥃🔍",
                    "Джин, от которого даже английская королева может сделать 'чёрт побери'! 🥃👑",
                    "Текила, после которой просыпаешься не только с кактусом, но и с мексиканским паспортом! 🌵🥃"
                ])
            elif any(word in post_lower for word in ['музык', 'диджей', 'концерт', 'фестивал', 'танц', 'live']):
                response = random.choice([
                    "Музыка - душа любой вечеринки! 🎵💃",
                    "Диджей просто огонь! 🔥🎧",
                    "Фестиваль мечты! Жду не дождусь! 🤩🎪",
                    "Танцы до упаду! 💃🕺",
                    "Музыка, которая бьет прямо в сердце! 💘🎵",
                    "Концерт, который запомнится навсегда! 🌟🎤",
                    "Звучит лучше, чем в мечтах! 🎶✨",
                    "Бас-бочка такая мощная, что у соседей посуда сама танцует! 🥁💃",
                    "Диджей сводит так, что даже пьяный дядя Вася у турникета начинает разбираться в жанрах! 🎧🤓",
                    "Фестиваль, на котором дождь - это не погода, а перкуссионный инструмент! 🌧️🎵",
                    "Музыка настолько громкая, что Shazam сдался и просто написал 'да, это огонь'! 🔥📱",
                    "Танцы такие зажигательные, что пожарная служба уже наготове! 💃🚒"
                ])
            elif any(word in post_lower for word in ['еда', 'бургер', 'закуск', 'гастроном', 'кухн', 'рецепт']):
                response = random.choice([
                    "Еда, от которой слюнки текут! 🤤🍔",
                    "Гастрономический оргазм! 🍽️😍",
                    "Бургер - как объятие для желудка! 🤗🍔",
                    "Закуска, ради которой стоит пить! 🍻🥨",
                    "Вкусно до слез! 😭🍕",
                    "Еда, которая греет душу! 🔥🍲",
                    "Настоящее кулинарное искусство! 👨🍳🎨",
                    "Бургер настолько сочный, что для его поедания нужно подписыть договор с прачечной! 🍔🚿",
                    "Закуска, ради которой можно простить измену. Ну, почти. 🥨😠",
                    "Гастрономический шедевр, после которого хочется аплодировать повару стоя. И плакать. 🍽️👏😭",
                    "Еда, от которой инстаграм плачет от счастья, а диетолог - от горя. 📸🍔😭",
                    "Это не закуска, это спасательный круг для твоего похмелья! 🥨"
                ])
            elif any(word in post_lower for word in ['вечеринк', 'тусовк', 'party', 'ночь', 'клуб']):
                response = random.choice([
                    "Вечеринка мечты! 🎉🌟",
                    "Ночь, которую не забудешь! 🌙✨",
                    "Тусовка огонь! Жаль, что я не с вами! 🔥😢",
                    "Party like there's no tomorrow! 💃🕺",
                    "Клуб, где рождаются легенды! 👑🎪",
                    "Вечеринка, от которой болит все, кроме души! 💪😂",
                    "Ночь безумия и веселья! 🌃🎊",
                    "Вечеринка настолько крутая, что даже охранник у входа танцует лучше меня! 💃🕺",
                    "Тусовка, после которой 'привет, я твой диван' звучит как предложение руки и сердца! 🛋️💍",
                    "Ночь, которая закончилась там, где начинается легенда. И поиск ключей. 🌃🗝️",
                    "Party level: 'завтра утром буду жалеть, но сейчас - НЕТ!' 💪😂",
                    "Клуб, в котором даже лед в стакане танцует лучше меня. Но я стараюсь! 🧊💃"
                ])
            elif any(word in post_lower for word in ['розыгрыш', 'конкурс', 'подарок', 'приз', 'выигр']):
                response = random.choice([
                    "Розыгрыш - мечта сбывается! 🎁✨",
                    "Хочу выиграть этот приз! 🙏🎯",
                    "Конкурс, ради которого стоит жить! 🏆❤️",
                    "Подарок мечты! Хочу такой же! 🤩🎁",
                    "Удача, улыбнись мне! 🍀😊",
                    "Розыгрыш, который изменит жизнь! 🌟🎁",
                    "Приз, ради которого я готов на все! 💪🎯",
                    "Хочу этот приз так сильно, что готов подписаться на рассылку даже от тёти Глаши! 📧🎁",
                    "Розыгрыш, ради которого я создал 15 фейковых аккаунтов. Шучу. Или нет? 👀🎯",
                    "Этот подарок нужен мне больше, чем рыбаку - новая удочка. Ладно, может не совсем. 🎣🎁",
                    "Если я выиграю, обещаю делиться... фотографиями того, как им пользуюсь! 🤳🎁",
                    "Удача, будь ко мне благосклонна, как кот к тому, у кого вкусняшка! 🍀🐈"
                ])
            elif any(word in post_lower for word in ['дегустац', 'проб', 'вкус', 'аромат', 'букет']):
                response = random.choice([
                    "Дегустация - праздник для рецепторов! 👅🎉",
                    "Вкус, от которого мурашки! 🥶👌",
                    "Аромат, который сводит с ума! 🤯👃",
                    "Букет, достойный королей! 👑🍷",
                    "Дегустация, которая открывает новые горизонты! 🌅🍺",
                    "Вкусовой взрыв! 💥😋",
                    "Настоящее наслаждение для гурмана! 😌🍽️",
                    "Дегустация, после которой мой язык получил Нобелевскую премию по вкусоведению! 👅🏆",
                    "Аромат такой сложный, что для его описания не хватит одного носа! 👃👃",
                    "После этой пробы понимаешь, что до этого ты не жил, а просто жевал! 😮🍷",
                    "Вкусовые рецепторы танцуют ламбаду, а нос - танго! 👃💃🕺",
                    "Букет настолько изысканный, что хочется извиниться перед своим прошлым алкогольным опытом. 🍷🙏"
                ])
            else:
                response = random.choice([
                    "Отличный пост! Жду продолжения! 🔥📝",
                    "Контент, который заряжает энергией! ⚡😄",
                    "После такого хочется творить! 🎨✨",
                    "Этот пост - pure gold! 🏆👏",
                    "Выдаете как всегда на высоте! 🚀💫",
                    "Контент уровня богов! 👑🌟",
                    "Пост, который делает день лучше! ☀️❤️",
                    "Информация, ради которой стоит жить! 💪📚",
                    "Бомбический контент! 💣🔥",
                    "Настоящее искусство постинга! 🎭📱",
                    "Этот пост настолько хорош, что я простил ему даже отсутствие алкоголя в кадре! 📝❤️",
                    "Контент, от которого у алгоритма лента просит добавки! 🤖🍽️",
                    "После такого поста хочется творить, любить и заказывать пиццу. Одновременно! 🎨❤️🍕",
                    "Это не пост, это духовная скрепка для моей ленты! 📎✨",
                    "Информация, которая греет душу лучше, чем глинтвейн в декабре! 🔥📚",
                    "Бомбический контент! Даже спам-боты ставят лайки! 💣🤖",
                    "Пост уровня 'я это покажу своим будущим детям как пример качественного контента'! 👶📱",
                    "Этот контент стоит того, чтобы за него платить. Но я, конечно, бесплатно потреблю. 😏📝"
                ])

            responses.append({"post": post, "response": response})
            if (i + 1) % 20 == 0:
                print(f"🎯 Сгенерировано {i + 1} ответов...")

        print(f"✅ Всего сгенерировано {len(responses)} ответов")
        return responses


class SimpleModelTrainer:
    """Упрощенный тренер модели"""

    def __init__(self, base_model="sberbank-ai/rugpt3small_based_on_gpt2"):
        self.tokenizer = GPT2Tokenizer.from_pretrained(base_model)
        self.model = GPT2LMHeadModel.from_pretrained(base_model)

        # Устанавливаем pad_token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def prepare_training_data(self, posts_responses):
        """Подготовка данных для обучения"""
        training_texts = []

        for item in posts_responses:
            # Формируем текст для обучения
            text = f"POST: {item['post']} RESPONSE: {item['response']}{self.tokenizer.eos_token}"
            training_texts.append(text)

        return training_texts

    def train(self, training_texts, output_dir="./my_trained_model"):
        """Обучение модели"""
        print(f"📚 Подготовка {len(training_texts)} примеров для обучения...")

        # Создаем датасет
        dataset = Dataset.from_dict({"text": training_texts})

        # Токенизируем
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding=False,
                max_length=128,
                return_tensors=None
            )

        tokenized_dataset = dataset.map(tokenize_function, batched=True)

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,
        )

        # Упрощенные аргументы обучения
        training_args = TrainingArguments(
            output_dir=output_dir,
            overwrite_output_dir=True,
            num_train_epochs=3,
            per_device_train_batch_size=2,
            save_steps=10000,
            save_total_limit=2,
            logging_steps=50,
            learning_rate=5e-5,
            weight_decay=0.01,
            warmup_steps=100,
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
        )

        print("🚀 Начинаю обучение модели...")
        trainer.train()

        # Сохраняем модель
        trainer.save_model()
        self.tokenizer.save_pretrained(output_dir)
        print(f"✅ Модель обучена и сохранена в {output_dir}")


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


# Основной процесс сбора и обучения
async def main():
    """Сбор данных и обучение модели"""
    CHANNEL = '@stepiveter'

    # 1. Создаем клиент и авторизуемся
    print("📊 Этап 1: Создание клиента...")
    client = await create_client('data_collector_session')

    # 2. Собираем данные
    print("📊 Этап 2: Сбор данных...")
    collector = DataCollector()
    posts = await collector.collect_posts(client, CHANNEL, limit=10000)

    # 3. Отключаем клиент после сбора данных
    await client.disconnect()

    # 4. Генерируем ответы
    print("🎯 Этап 3: Генерация ответов...")
    response_gen = ResponseGenerator()
    training_data = response_gen.generate_responses(posts)

    # 5. Сохраняем данные
    with open('training_data.json', 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    print(f"💾 Данные сохранены в training_data.json ({len(training_data)} примеров)")

    # 6. Обучаем модель
    print("🚀 Этап 4: Обучение модели...")
    trainer = SimpleModelTrainer()
    training_texts = trainer.prepare_training_data(training_data)
    trainer.train(training_texts)

    print("🎉 Обучение завершено! Модель готова к использованию.")


if __name__ == "__main__":
    asyncio.run(main())
