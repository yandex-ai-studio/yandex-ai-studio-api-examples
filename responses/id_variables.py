import openai

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "...."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)
response = client.responses.create(
    prompt={
        "id": "........",
        "variables": {
            "city": "Иркутск",
            "friends_number": "3"
        }
    },
    input="Куда пойти вечером?",
)
print(response.output_text)
