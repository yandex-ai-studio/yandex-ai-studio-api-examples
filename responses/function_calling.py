import json
import openai

# 1. Настройки подключения
YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    project=YANDEX_CLOUD_FOLDER,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
)

# 2. Описываем инструмент (функцию), доступный модели
available_tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Получить текущую погоду для указанного города.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Название города, например: Москва или Красноярск",
                },
            },
            "required": ["city"],
        },
    },
]


# 3. Пример реализации функции (мок)
def get_weather(city: str):
    return {
        "город": city,
        "температура": "12 °C",
        "состояние": "Облачно, лёгкий ветер",
    }


# 4. Первый запрос от пользователя
first = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    tools=available_tools,
    input="Какая сейчас погода в Питере?",
)

print("Первый ответ модели:")

# --- Новый блок вывода информации о вызванной функции ---
for item in getattr(first, "output", []):
    if getattr(item, "type", "") == "function_call":
        print(f"Модель вызвала функцию: {item.name}")
        print("Аргументы:")
        try:
            args = json.loads(item.arguments)
            print(json.dumps(args, ensure_ascii=False, indent=2))
        except Exception:
            print(item.arguments)
        print()  # пустая строка для читаемости

# 5. Проверяем, есть ли вызов функции
calls = [it for it in first.output if getattr(it, "type", "") == "function_call"]

for call in calls:
    if call.name != "get_weather":
        continue

    args = json.loads(getattr(call, "arguments", "{}") or "{}")
    result = get_weather(**args)

    # 6. Отправляем результат вызова функции как input + связываем previous_response_id
    second = client.responses.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        tools=available_tools,
        instructions="Добавляй в ответ подходящие эмоджи.",
        previous_response_id=first.id,
        input=[
            {
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            }
        ],
    )

    print("Финальный ответ модели:")
    print(second.output_text)