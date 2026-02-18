import openai
import json

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)

response = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    input="Сделай краткий обзор новостей про LLM за сентябрь 2025 года.",
    tools=[
        {
                "type": "web_search",
                "filters": {
                    # до 5 штук
                    "allowed_domains": [
                        "..."
                    ],
                    "user_location": {
                        "region": "213",
                    }
                }
            }
    ],
    temperature=0.3,
    max_output_tokens=1000
)

# Текст ответа
print("Текст ответа:")
print(response.output_text)
print("\n" + "=" * 50 + "\n")

# Полный ответ
print("Полный ответ (JSON):")
print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))
