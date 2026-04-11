#!/usr/bin/env python3
"""
Голосовой агент без функций (function calling)
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
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
VOICE = "dasha"

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


# Паттерны для детекции автоответчика
ANSWERING_MACHINE_PATTERNS = [
    r'нажмите\s+\d+',  # "нажмите 1", "нажмите 2"
    r'нажмите\s+(один|два|три|четыре|пять|шесть|семь|восемь|девять|ноль)',  # "нажмите один", "нажмите два"
    r'для\s+\w+\s+нажмите',  # "для продолжения нажмите"
    r'оставьте\s+сообщение',  # "оставьте сообщение"
    r'после\s+сигнала',  # "после сигнала"
    r'голосовое\s+меню',  # "голосовое меню"
    r'автоответчик',  # "автоответчик"
    r'выберите\s+\d+',  # "выберите 1"
    r'выберите\s+(один|два|три|четыре|пять|шесть|семь|восемь|девять|ноль)',  # "выберите один"
    r'для\s+связи\s+с\s+оператором',  # "для связи с оператором"
    r'перевод\s+на\s+оператора',  # "перевод на оператора"
    r'ожидайте\s+ответа',  # "ожидайте ответа"
    r'все\s+операторы\s+заняты',  # "все операторы заняты"
    r'звонок\s+будет\s+записан',  # "звонок будет записан"
    r'для\s+качества\s+обслуживания',  # "для качества обслуживания"
]


def detect_answering_machine_by_text(text: str) -> tuple[bool, str]:
    """
    Проверяет текст на наличие признаков автоответчика
    Возвращает (True, причина) если обнаружен автоответчик, иначе (False, "")
    """
    text_lower = text.lower()
    
    for pattern in ANSWERING_MACHINE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, f"Обнаружен паттерн автоответчика: '{pattern}' в тексте: '{text}'"
    
    return False, ""


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Флаг для завершения диалога
dialog_should_end = False

# Флаг что функция завершения уже вызвана (чтобы предотвратить повторные вызовы)
termination_function_called = False

# Флаг что нужно закрыть соединение после завершения текущего ответа
close_after_response = False

# Накопление текста ответа модели
current_response_text = ""


def process_function_call(item):
    """Обработка вызова функций"""
    call_id = item.get("call_id")
    function_name = item.get("name")
    args_text = item.get("arguments") or "{}"

    try:
        args = json.loads(args_text)
    except json.JSONDecodeError:
        args = {}

    # Обработка функций
    if function_name == "goodbye":
        message = args.get("message", "До свидания!")
        summary = args.get("summary", "")
        # Возвращаем сообщение в JSON формате для озвучки моделью
        output = json.dumps({
            "message": message,
            "summary": summary
        }, ensure_ascii=False)
        # Выводим информацию о завершении диалога
        print("\n" + "="*80)
        print("👋 ЗАВЕРШЕНИЕ ДИАЛОГА 👋")
        print("="*80)
        print(f"📝 Саммари диалога:\n   {summary}")
        print("="*80 + "\n")
        logger.info(f"Завершение диалога: summary={summary}")
    elif function_name == "detect_answering_machine":
        summary = args.get("summary", "")
        reason = args.get("reason", "")
        # Возвращаем информацию в JSON формате
        output = json.dumps({
            "summary": summary,
            "reason": reason
        }, ensure_ascii=False)
        # Выводим информацию об обнаружении автоответчика
        print("\n" + "="*80)
        print("🤖 ОБНАРУЖЕН АВТООТВЕТЧИК 🤖")
        print("="*80)
        print(f"📝 Причина:\n   {reason}")
        print(f"📝 Саммари диалога:\n   {summary}")
        print("="*80 + "\n")
        logger.info(f"Обнаружен автоответчик: reason={reason}, summary={summary}")
    elif function_name == "transfer_to_operator":
        message = args.get("message", "Ожидайте, перевожу на оператора.")
        summary = args.get("summary", "")
        category = args.get("category", "general")
        # Возвращаем все параметры в JSON формате
        output = json.dumps({
            "message": message,
            "summary": summary,
            "category": category
        }, ensure_ascii=False)
        # Выводим информацию о переводе
        print("\n" + "="*80)
        print("🔄 ПЕРЕВОД НА ОПЕРАТОРА 🔄")
        print("="*80)
        print(f"📋 Категория: {category.upper()}")
        print(f"📝 Саммари диалога:\n   {summary}")
        print("="*80 + "\n")
        logger.info(f"Перевод на оператора: category={category}, summary={summary}")
    else:
        output = json.dumps({"error": "Unknown function"}, ensure_ascii=False)

    return {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output
        }
    }


# ======== Основное приложение ========

async def setup_session(ws):
    """Настройка сессии"""

    await ws.send_json({
        "type": "session.update",
        "session": {
            "instructions": (
                "Ты голосовой ассистент. Помогаешь с ответами на вопросы. Отвечаешь кратко и по делу. "
                "Старайся помочь пользователю самостоятельно. "
                "\n\nКРИТИЧЕСКИ ВАЖНО О ВЫЗОВЕ ФУНКЦИЙ: "
                "\n- Вызов функции - это ВНУТРЕННЯЯ операция, которую пользователь НЕ должен слышать"
                "\n- НИКОГДА не произноси вслух сам вызов функции (например 'transfer_to_operator(...)' или 'goodbye(...)')"
                "\n- Пользователь услышит только то, что ты передашь в параметре 'message'"
                "\n- ЗАПРЕЩЕНО отвечать текстом вместо вызова функции!"
                "\n- ВАЖНО: Функции goodbye, transfer_to_operator и detect_answering_machine вызываются ТОЛЬКО ОДИН РАЗ! После вызова НЕ нужно ничего больше делать!"
                "\n\nОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ ФУНКЦИИ В ЭТИХ СЛУЧАЯХ: "
                "\n1) Если ты понимаешь, что разговариваешь с АВТООТВЕТЧИКОМ (слышишь записанное сообщение, голосовое меню, 'нажмите 1', 'оставьте сообщение после сигнала') - "
                "НЕМЕДЛЕННО вызови функцию detect_answering_machine с параметрами:"
                "\n  - summary: краткое резюме в ТРЕТЬЕМ ЛИЦЕ (что услышал ассистент)"
                "\n  - reason: почему ты решил, что это автоответчик (например: 'Услышано голосовое меню с вариантами выбора')"
                "\n\n2) Когда пользователь прощается ('пока', 'до свидания', 'всего доброго') - "
                "ОБЯЗАТЕЛЬНО вызови функцию goodbye с параметрами:"
                "\n  - message: прощальное сообщение (например: 'До свидания!')"
                "\n  - summary: краткое резюме диалога в ТРЕТЬЕМ ЛИЦЕ (что обсуждалось)"
                "\nНЕ отвечай текстом 'до свидания', ВЫЗОВИ ФУНКЦИЮ!"
                "\n\n3) Когда пользователь ЯВНО ПРОСИТ оператора/живого человека/поддержку "
                "(говорит 'соедини с оператором', 'хочу поговорить с человеком', 'переведи на оператора', 'дай оператора') - "
                "ОБЯЗАТЕЛЬНО вызови функцию transfer_to_operator. "
                "НЕ отвечай текстом 'сейчас соединю', ВЫЗОВИ ФУНКЦИЮ transfer_to_operator с параметрами:"
                "\n  - message: что озвучить пользователю (например: 'Сейчас соединю с оператором') "
                "\n  - summary: ОБЯЗАТЕЛЬНО опиши весь диалог в 1-2 предложениях в ТРЕТЬЕМ ЛИЦЕ или нейтрально. "
                "НЕ используй 'я' - пиши 'ассистент' или безличные конструкции. "
                "Пример: 'Пользователь сообщил о проблеме с клавишей. Ассистент запросил детали' или 'Обсуждалась проблема с западающей клавишей на ноутбуке' "
                "\n  - category: 'support' для техподдержки/проблем, 'general' для остального "
                "\n\nВАЖНО: НЕ переводи на оператора автоматически! Только если пользователь САМ ПОПРОСИТ! "
                "Если пользователь просто описывает проблему - помоги ему сам, задай уточняющие вопросы. "
                "\n\nЕЩЕ РАЗ: Когда нужно перевести на оператора - ВЫЗОВИ ФУНКЦИЮ transfer_to_operator, а НЕ отвечай текстом!"
            ),
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": IN_RATE
                    },
                    "turn_detection": {
                        "type": "server_vad",  # включаем серверный VAD
                        "threshold": 0.4,  # чувствительность
                        "silence_duration_ms": 400,  # длительность тишины для завершения речи
                    },
                },
                "output": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": OUT_RATE
                    },
                    "voice": VOICE,
                },
            },
            # Инструменты для использования в агенте
            "tools": [
                {
                    "type": "function",
                    "name": "detect_answering_machine",
                    "description": "Обнаружен автоответчик или голосовое меню. Вызывай НЕМЕДЛЕННО, если слышишь записанное сообщение, голосовое меню, инструкции типа 'нажмите 1', 'оставьте сообщение после сигнала' и т.п.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "ОБЯЗАТЕЛЬНО: Краткое резюме в ТРЕТЬЕМ ЛИЦЕ - что услышал ассистент (например: 'Ассистент услышал голосовое меню с вариантами выбора')"
                            },
                            "reason": {
                                "type": "string",
                                "description": "ОБЯЗАТЕЛЬНО: Причина, почему ты решил что это автоответчик (например: 'Услышано голосовое меню', 'Предложено оставить сообщение после сигнала', 'Автоматическое приветствие с вариантами выбора')"
                            }
                        },
                        "required": ["summary", "reason"],
                        "additionalProperties": False
                    }
                },
                {
                    "type": "function",
                    "name": "goodbye",
                    "description": "Попрощаться с пользователем и завершить диалог. Вызывай когда пользователь прощается. ОБЯЗАТЕЛЬНО передай summary диалога.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Прощальное сообщение для произнесения"
                            },
                            "summary": {
                                "type": "string",
                                "description": "ОБЯЗАТЕЛЬНО: Краткое резюме ВСЕГО диалога в 1-2 предложениях в ТРЕТЬЕМ ЛИЦЕ или нейтрально. НЕ используй 'я' - пиши 'ассистент' или безличные конструкции. Опиши о чем спрашивал пользователь и что ему ответил ассистент."
                            }
                        },
                        "required": ["message", "summary"],
                        "additionalProperties": False
                    }
                },
                {
                    "type": "function",
                    "name": "transfer_to_operator",
                    "description": "Перевести пользователя на живого оператора. Вызывай когда пользователь просит связаться с оператором или живым человеком. ОБЯЗАТЕЛЬНО передай все три параметра.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Вежливое сообщение для озвучки пользователю (например: 'Ожидайте, перевожу на оператора')"
                            },
                            "summary": {
                                "type": "string",
                                "description": "ОБЯЗАТЕЛЬНО: Краткое резюме ВСЕГО диалога в 1-2 предложениях в ТРЕТЬЕМ ЛИЦЕ или нейтрально. НЕ используй 'я' - пиши 'ассистент' или безличные конструкции. Опиши о чем спрашивал пользователь и что ему ответил ассистент. Это важно для оператора!"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["support", "general"],
                                "description": "Категория запроса: 'support' - если вопрос о технических проблемах/поддержке/неполадках, 'general' - для всех остальных вопросов (тарифы, услуги, общая информация)"
                            }
                        },
                        "required": ["message", "summary", "category"],
                        "additionalProperties": False
                    }
                }
            ]
        }
    })


# pylint: disable-next=too-many-branches
async def downlink(ws, audio_out):
    """Приём и обработка сообщений от сервера"""
    # Управление "эпохами" озвучки
    play_epoch = 0
    current_response_epoch = None
    # Накопление текста ответа
    global current_response_text, termination_function_called, close_after_response, dialog_should_end
    current_response_text = ""

    try:
        async for msg in ws:
            # Проверяем флаг завершения диалога
            if dialog_should_end:
                logger.info("Завершаем downlink по флагу dialog_should_end")
                break
            
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
                        
                        # Проверка на автоответчик по регулярным выражениям
                        is_answering_machine, reason = detect_answering_machine_by_text(transcript)
                        if is_answering_machine and not termination_function_called:
                            logger.warning(f"🤖 Автоответчик обнаружен по регулярному выражению: {reason}")
                            
                            # Формируем саммари на основе текущего диалога
                            summary = f"Обнаружен автоответчик. Транскрипт: '{transcript}'"
                            
                            # Выводим результат
                            print(f"\n{'='*60}")
                            print(f"🤖 АВТООТВЕТЧИК ОБНАРУЖЕН (regex)")
                            print(f"{'='*60}")
                            print(f"Причина: {reason}")
                            print(f"Саммари: {summary}")
                            print(f"{'='*60}\n")
                            
                            # Устанавливаем флаги для завершения
                            termination_function_called = True
                            dialog_should_end = True
                            
                            # Закрываем соединение
                            await ws.close()
                            logger.info("WebSocket соединение закрыто после обнаружения автоответчика")

                # Текст, который сервер отправляет на озвучку
                case "response.output_text.delta":
                    delta = message.get("delta", "")
                    if delta:
                        current_response_text += delta
                        logger.info("on_message %s: [agent (text): %r]", msg_type, delta)
                
                # Текст ответа завершен
                case "response.output_text.done":
                    if current_response_text:
                        print(f"\n[ПОЛНЫЙ ОТВЕТ МОДЕЛИ]: {current_response_text}\n")
                        current_response_text = ""

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
                    current_response_text = ""  # Очищаем текст при начале нового ответа

                # Поступают аудиоданные от ассистента
                case "response.output_audio.delta":
                    if current_response_epoch == play_epoch:
                        delta = message["delta"]
                        decoded = b64_decode(delta)
                        logger.debug("on_message %s: got %d bytes", msg_type, len(decoded))
                        await audio_out.write(decoded)

                case "response.output_item.done":
                    item = message.get("item") or {}
                    if item.get("type") != 'function_call':
                        logger.info(
                            'on_message %s: got non-function call payload %r',
                            msg_type, item
                        )
                        continue

                    function_name = item.get("name")
                    
                    # Проверяем, не была ли уже вызвана функция завершения
                    if function_name in ["goodbye", "transfer_to_operator", "detect_answering_machine"]:
                        if termination_function_called:
                            logger.warning(f"Функция {function_name} уже была вызвана, игнорируем повторный вызов")
                            continue
                        termination_function_called = True
                    
                    # Обрабатываем вызов функции
                    payload_item = process_function_call(item)
                    logger.info(
                        "[conversation.item.create(function_call_output): %r]",
                        payload_item,
                    )
                    await ws.send_json(payload_item)
                    
                    # Запрашиваем новый ответ агента (для озвучки результата функции)
                    logger.info("отправляем response.create после функции %s", function_name)
                    await ws.send_json({
                        "type": "response.create"
                    })
                    
                    # Если это функция завершения - устанавливаем флаг закрытия после ответа
                    if function_name in ["goodbye", "transfer_to_operator", "detect_answering_machine"]:
                        close_after_response = True
                        logger.info(f"Функция {function_name} вызвана, соединение будет закрыто после озвучки")

                case "error":
                    logger.error("ОШИБКА СЕРВЕРА: %r", json.dumps(message, ensure_ascii=False))

                case "response.done":
                    logger.info('on_message %s: [можно добавить ваш обработчик]', msg_type)
                    # Если установлен флаг закрытия после ответа - закрываем соединение
                    if close_after_response:
                        logger.info("Ответ модели завершен, закрываем соединение")
                        dialog_should_end = True
                        await ws.close()
                        logger.info("WebSocket соединение закрыто")
                
                case other:
                    logger.info('on_message %s: [можно добавить ваш обработчик]', other)
    
    finally:
        logger.info("WS соединение закрыто")


async def uplink(ws):
    """Отправка аудио с микрофона на сервер"""
    mic = AsyncMicrophone(samplerate=IN_RATE)
    async for pcm in mic:
        # Проверяем флаг завершения диалога
        global dialog_should_end
        if dialog_should_end:
            logger.info("Завершаем uplink по флагу dialog_should_end")
            break
            
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
