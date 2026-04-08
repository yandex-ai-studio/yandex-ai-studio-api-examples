#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys

import aiohttp

# Вспомогательные классы для работы с аудио. Можно использовать, можно реализовать самостоятельно.
# pip install yandex-ai-studio-sdk
from yandex_ai_studio_sdk._experimental.audio.microphone import AsyncMicrophone
from yandex_ai_studio_sdk._experimental.audio.out import AsyncAudioOut

assert sys.version_info >= (3, 10), "Python 3.10+ is required"

# Настройки API

# Конфигурация аудио для сервера
IN_RATE = 44100
OUT_RATE = 44100
VOICE = "zhanar"
ROLE = "friendly"

# Креды Облака
YANDEX_CLOUD_FOLDER_ID = "..."
YANDEX_CLOUD_API_KEY = "..."

# Проверяем, что заданы ключ и ID каталога
assert YANDEX_CLOUD_FOLDER_ID and YANDEX_CLOUD_API_KEY, "YANDEX_CLOUD_FOLDER_ID и YANDEX_CLOUD_API_KEY обязательны"

WSS_URL = (
    f"wss://ai.api.cloud.yandex.net/v1/realtime"
    f"?model=gpt://{YANDEX_CLOUD_FOLDER_ID}/speech-realtime-250923"
)

HEADERS = {"Authorization": f"Api-Key {YANDEX_CLOUD_API_KEY}"}


# ======== Вспомогательные функции ========

# Декодирует строку base64 в байты
def b64_decode(s: str) -> bytes:
    return base64.b64decode(s)


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
                "Ты дружелюбный голосовой ассистент. "
                "Помогаешь с ответами на вопросы. "
                "Отвечаешь кратко и по делу. "
                "Общаешься естественно и приятно. Твой язык общения — казахский."
            ),
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": IN_RATE
                    },
                    "languages": ["kk-KZ"],
                    "turn_detection": {
                        "type": "server_vad",  # включаем серверный VAD
                        "threshold": 0.5,  # чувствительность
                        "silence_duration_ms": 400,  # длительность тишины для завершения речи
                    },
                },
                "output": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": OUT_RATE
                    },
                    "voice": VOICE,
                    "role:": ROLE,
                },
            }
        }
    })


# pylint: disable-next=too-many-branches
async def downlink(ws, audio_out):
    """Приём и обработка сообщений от сервера"""
    # Управление "эпохами" озвучки
    play_epoch = 0
    current_response_epoch = None

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
                    logger.info("on_message %s: [user (transcript): %r]", msg_type, transcript)

            # Текст, который сервер отправляет на озвучку
            case "response.output_text.delta":
                delta = message.get("delta", "")
                if delta:
                    logger.info("on_message %s: [agent (text): %r]", msg_type, delta)

            # Логируем id сессии
            case "session.created":
                session_id = (message.get("session") or {}).get("id")
                logger.info("on_message %s: [session.id = %r]", msg_type, session_id)

            # Пользователь начал говорить — прерываем текущий ответ
            case "input_audio_buffer.speech_started":
                play_epoch += 1
                current_response_epoch = None
                logger.debug("on_message %s: clear audio out buffer", msg_type)
                await audio_out.clear()

            # Начало нового ответа ассистента
            case "response.created":
                current_response_epoch = play_epoch

            # Поступают аудиоданные от ассистента
            case "response.output_audio.delta":
                if current_response_epoch == play_epoch:
                    delta = message["delta"]
                    decoded = b64_decode(delta)
                    logger.debug("on_message %s: got %d bytes", msg_type, len(decoded))
                    await audio_out.write(decoded)

            case "error":
                logger.error("ОШИБКА СЕРВЕРА: %r", json.dumps(message, ensure_ascii=False))

            case other:
                logger.info('on_message %s: [можно добавить ваш обработчик]', other)

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
    print("Говорите (server VAD). Выход: Ctrl+C. Используйте наушники, чтобы избежать самопрерываний.")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
                logger.info("Подключено к Realtime API.")
                await setup_session(ws)

                async with AsyncAudioOut(samplerate=OUT_RATE) as audio_out:
                    await asyncio.gather(
                        uplink(ws),
                        downlink(ws, audio_out)
                    )
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        logger.info("Выход.")


if __name__ == "__main__":
    asyncio.run(main())
