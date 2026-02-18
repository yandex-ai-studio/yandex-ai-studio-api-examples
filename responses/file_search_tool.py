import openai
import json

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"
VECTOR_STORE_ID = "..."

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)

response = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    instructions="ты умный ассистент. если спрашивают про ... - ищи в подключенном индексе",
    tools=[{
        "type": "file_search",
        "vector_store_ids": [VECTOR_STORE_ID]
    }],
    input="что такое ..."
)

print("Текст ответа:")
print(response.output_text)
print("\n" + "=" * 50 + "\n")

# Полный ответ
print("Полный ответ (JSON):")
print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))
Строк: 31
Символов: 843
Байт: 940
