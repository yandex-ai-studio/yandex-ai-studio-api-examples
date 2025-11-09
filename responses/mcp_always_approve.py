import openai
import json

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    project=YANDEX_CLOUD_FOLDER,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
)

response = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    tools=[
        {
            "type": "mcp",
            "server_label": "kontur",
            "server_description": "Возвращает информацию по ИНН",
            "server_url": "...",  # URL MCP
            "require_approval": "never",
        },
    ],
    input="Чей ИНН ...",
)

# Текст ответа
print("Текст ответа:")
print(response.output_text)
print("\n" + "=" * 50 + "\n")

# Полный ответ
print("Полный ответ (JSON):")
print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))
