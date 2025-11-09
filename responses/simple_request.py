import openai

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
    instructions="Ты креативный ассистент. Помогаешь с генерацией идей.",
    input="Придумай 3 необычные идеи для стартапа в сфере путешествий.",
    temperature=0.4,
    max_output_tokens=1500
)

print(response.output_text)
