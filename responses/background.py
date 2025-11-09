import openai
import time

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    project=YANDEX_CLOUD_FOLDER,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
)

# 1. Создаём задачу в фоне
resp = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    input="Какие планеты есть в Солнечной системе?",
    background=True
)

print("Задача отправлена:", resp.id)

# 2. Опрашиваем статус
while True:
    status = client.responses.retrieve(resp.id)
    print("Статус:", status.status)
    if status.status in ["completed", "failed", "cancelled"]:
        break
    time.sleep(1)

# 3. Получаем результат
if status.status == "completed":
    print("Готовый ответ:", status.output_text)
else:
    print("Ошибка:", status.status)
