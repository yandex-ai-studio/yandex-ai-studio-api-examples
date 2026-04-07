#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys

import aiohttp

# Вспомогательные классы для работы с аудио
# pip install yandex-ai-studio-sdk
from yandex_ai_studio_sdk._experimental.audio.microphone import AsyncMicrophone

assert sys.version_info >= (3, 10), "Python 3.10+ is required"

# Конфигурация аудио для сервера
IN_RATE = 44100

# ==== Креды Облака ====
YANDEX_CLOUD_FOLDER_ID = "..."
YANDEX_CLOUD_API_KEY = "..."

# Проверяем, что заданы ключ и ID каталога
assert YANDEX_CLOUD_FOLDER_ID and YANDEX_CLOUD_API_KEY, "YANDEX_CLOUD_FOLDER_ID и YANDEX_CLOUD_API_KEY обязательны"

WSS_URL = (
    f"wss://ai.api.cloud.yandex.net/v1/realtime"
    f"?model=gpt://{YANDEX_CLOUD_FOLDER_ID}/speech-realtime-250923"
)

HEADERS = {"Authorization": f"api-key {YANDEX_CLOUD_API_KEY}"}


# ======== Вспомогательные функции ========

# Кодирует байты в строку base64
def b64_encode(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ======== Основное приложение ========

async def setup_session(ws):
    """Настройка сессии"""

    await ws.send_json({
        "type": "session.update",
        "session": {
            "instructions": """
РОЛЬ И ЗАДАЧА
Ты — агент для нормализации текста, полученного из голосового ввода, с извлечением сущностей.

ТВОЯ ЗАДАЧА
Принимай реплику пользователя и возвращай JSON-объект с:
1. Нормализованным текстом
2. Извлечёнными сущностями

ПРАВИЛА НОРМАЛИЗАЦИИ
1. Убери слова-паразиты (ну, вот, типа, как бы, э-э-э)
2. Исправь орфографические и грамматические ошибки
3. Расставь правильную пунктуацию
4. Исправь падежи, склонения, спряжения
5. Приведи к литературной норме русского языка
6. Сохрани смысл и эмоциональную окраску

ИЗВЛЕКАЕМЫЕ СУЩНОСТИ
Ищи и извлекай следующие типы сущностей:
- **addresses** (адреса): улицы, дома, города, районы, ориентиры
- **times** (время): конкретное время, временные промежутки, даты
- **dates** (даты): числа, месяцы, годы, дни недели
- **names** (имена): имена людей, фамилии
- **organizations** (организации): названия компаний, учреждений
- **locations** (локации): названия мест, павильонов, зданий
- **phone_numbers** (телефоны): номера телефонов
- **emails** (email): адреса электронной почты
- **products** (товары/услуги): названия товаров, блюд, услуг
- **amounts** (суммы): денежные суммы, количества

ФОРМАТ ОТВЕТА
Верни ТОЛЬКО валидный JSON без дополнительного текста:

```json
{
  "normalized_text": "нормализованный текст",
  "entities": {
    "addresses": ["адрес1", "адрес2"],
    "times": ["время1"],
    "dates": ["дата1"],
    "names": ["имя1"],
    "organizations": ["организация1"],
    "locations": ["локация1"],
    "phone_numbers": ["телефон1"],
    "emails": ["email1"],
    "products": ["товар1", "товар2"],
    "amounts": ["сумма1"]
  }
}
```

Если какой-то тип сущностей не найден, не включай его в объект entities или оставь пустым массивом.

ПРИМЕРЫ

Пользователь: "ну типа я хотел бы узнать эээ когда будет готов заказ"
Ты:
```json
{
  "normalized_text": "Я хотел бы узнать, когда будет готов заказ.",
  "entities": {}
}
```

Пользователь: "подскажите как можно проехать к такому то павильону на вднх"
Ты:
```json
{
  "normalized_text": "Подскажите, как можно проехать к такому-то павильону на ВДНХ.",
  "entities": {
    "locations": ["ВДНХ", "павильон"]
  }
}
```

Пользователь: "знаете я хочу заказать чизбургера с четыре сыра тысяча островов и вообще манго маракуйя"
Ты:
```json
{
  "normalized_text": "Знаете, я хочу заказать чизбургер с четырьмя сырами и соусом «Тысяча островов», а также манго-маракуйю.",
  "entities": {
    "products": ["чизбургер с четырьмя сырами", "соус «Тысяча островов»", "манго-маракуйя"]
  }
}
```

Пользователь: "запишите меня на завтра на три часа дня к доктору иванову"
Ты:
```json
{
  "normalized_text": "Запишите меня на завтра на три часа дня к доктору Иванову.",
  "entities": {
    "dates": ["завтра"],
    "times": ["15:00"],
    "names": ["Иванов"]
  }
}
```

Пользователь: "мой адрес москва ленинский проспект дом двадцать три квартира пять позвоните мне на восемь девять один два три четыре пять шесть семь восемь девять"
Ту:
```json
{
  "normalized_text": "Мой адрес: Москва, Ленинский проспект, дом 23, квартира 5. Позвоните мне на 8-912-345-67-89.",
  "entities": {
    "addresses": ["Москва, Ленинский проспект, дом 23, квартира 5"],
    "phone_numbers": ["8-912-345-67-89"]
  }
}
```

ВАЖНО
- Возвращай ТОЛЬКО JSON, без дополнительного текста
- Не добавляй комментарии или пояснения
- Убедись, что JSON валидный
- Извлекай все найденные сущности
""",
            "output_modalities": ["text"],  # ТОЛЬКО ТЕКСТОВЫЙ ВЫВОД
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": IN_RATE
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "silence_duration_ms": 400,
                    },
                }
            },
            "tools": []  # БЕЗ ФУНКЦИЙ
        }
    })


async def downlink(ws):
    """Приём и обработка сообщений от сервера"""
    
    current_response = ""

    async for msg in ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
            logger.info('got non-text payload from websocket: %s', msg.data)
            continue

        message = json.loads(msg.data)
        msg_type = message.get("type")

        match msg_type:
            # Распознанный текст пользователя
            case "conversation.item.input_audio_transcription.completed":
                transcript = message.get("transcript", "")
                if transcript:
                    logger.info("[ПОЛЬЗОВАТЕЛЬ]: %s", transcript)

            # Текст ответа ассистента (JSON)
            case "response.output_text.delta":
                delta = message.get("delta", "")
                if delta:
                    current_response += delta
                    print(delta, end="", flush=True)

            # Завершение текстового ответа
            case "response.output_text.done":
                print()  # Новая строка
                
                # Попытка распарсить и красиво вывести JSON
                if current_response.strip():
                    try:
                        # Убираем markdown блоки если есть
                        json_text = current_response.strip()
                        if json_text.startswith("```json"):
                            json_text = json_text[7:]
                        if json_text.startswith("```"):
                            json_text = json_text[3:]
                        if json_text.endswith("```"):
                            json_text = json_text[:-3]
                        
                        parsed = json.loads(json_text.strip())
                        logger.info("📋 Результат:")
                        logger.info("  Нормализованный текст: %s", parsed.get("normalized_text", ""))
                        if parsed.get("entities"):
                            logger.info("  Сущности:")
                            for entity_type, values in parsed["entities"].items():
                                if values:
                                    logger.info("    - %s: %s", entity_type, values)
                    except json.JSONDecodeError:
                        logger.warning("Не удалось распарсить JSON ответ")
                
                current_response = ""

            # Логируем id сессии
            case "session.created":
                session_id = (message.get("session") or {}).get("id")
                logger.info("[SESSION] ID = %s", session_id)

            case "error":
                logger.error("ОШИБКА СЕРВЕРА: %r", json.dumps(message, ensure_ascii=False))

            case other:
                # Не логируем все события, только важные
                if other not in ["session.updated", "input_audio_buffer.speech_stopped", 
                                "input_audio_buffer.speech_started", "response.created",
                                "conversation.item.created", "response.content_part.added",
                                "response.content_part.done", "response.done"]:
                    logger.debug('on_message %s', other)

    logger.info("WS соединение закрыто")


async def uplink(ws):
    """Отправка аудио с микрофона на сервер"""
    mic = AsyncMicrophone(samplerate=IN_RATE)
    async for pcm in mic:
        logger.debug('send payload with size %d', len(pcm))

        try:
            await ws.send_json({
                "type": "input_audio_buffer.append",
                "audio": b64_encode(pcm)
            })
        except aiohttp.ClientConnectionResetError:
            logger.warning("unable to send new data due to websocket was closed")
            return


# Главный цикл приложения
async def main():
    print("\n=== Агент нормализации с извлечением сущностей ===")
    print("Говорите в микрофон, агент вернёт JSON с нормализованным текстом и сущностями.")
    print("Выход: Ctrl+C.\n")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
                logger.info("Подключено к Realtime API.")
                await setup_session(ws)

                await asyncio.gather(
                    uplink(ws),
                    downlink(ws)
                )
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        logger.info("\nВыход.")


if __name__ == "__main__":
    asyncio.run(main())
