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

# Настройки аудио
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
            "instructions": (
                "Ты дружелюбный голосовой ассистент-болталка. "
                "Помогаешь с ответами на вопросы, поддерживаешь беседу. "
                "Отвечаешь кратко и по делу, но с юмором когда уместно. "
                "Если просят рассказать новости или найти информацию в интернете — используй функцию web_search."
            ),
            "output_modalities": ["text"],  # ТОЛЬКО ТЕКСТОВЫЙ ВЫВОД
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": IN_RATE
                    },
                    "turn_detection": {
                        "type": "server_vad",  # включаем серверный VAD
                        "threshold": 0.5,  # чувствительность
                        "silence_duration_ms": 400,  # длительность тишины для завершения речи
                    },
                },
            },
            # Инструменты
            "tools": [
                # Встроенная функция для поиска в интернете
                {
                    "type": "function",
                    "name": "web_search",
                    "description": "Поиск в интернете",
                    "parameters": {}
                }
            ]
        }
    })


async def downlink(ws):
    """Приём и обработка сообщений от сервера"""

    async for msg in ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
            logger.info('got non-text payload from websocket: %s', msg.data)
            continue

        message = json.loads(msg.data)
        msg_type = message.get("type")

        match msg_type:
            # Распознанный текст пользователя (транскрипция)
            case "conversation.item.input_audio_transcription.completed":
                transcript = message.get("transcript", "")
                if transcript:
                    logger.info("[ВЫ]: %s", transcript)

            # Текст ответа ассистента
            case "response.output_text.delta":
                delta = message.get("delta", "")
                if delta:
                    print(delta, end="", flush=True)

            # Завершение текстового ответа
            case "response.output_text.done":
                print()  # Новая строка

            # Логируем id сессии
            case "session.created":
                session_id = (message.get("session") or {}).get("id")
                logger.info("[SESSION] ID = %s", session_id)

            case "response.output_item.done":
                item = message.get("item") or {}
                if item.get("type") != 'function_call':
                    continue


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
    print("\n╔══════════════════════════════════════════╗")
    print("║  Голосовой ввод - Текстовый вывод        ║")
    print("╚══════════════════════════════════════════╝")
    print("\nГоворите в микрофон (server VAD). Выход: Ctrl+C.")
    print("Используйте наушники, чтобы избежать самопрерываний.\n")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
                logger.info("Подключено к Realtime API.")
                await setup_session(ws)

                # Инициируем первый ответ ассистента
                logger.info("Отправляем начальное приветствие...")
                await ws.send_json({
                    "type": "response.create",
                    "response": {
                        "modalities": ["text"],
                        "conversation": "default",
                    }
                })

                await asyncio.gather(
                    uplink(ws),
                    downlink(ws)
                )
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        print("\n\n👋 До свидания!")


if __name__ == "__main__":
    asyncio.run(main())
