import openai

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "...."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)

response = client.responses.create(
    prompt={
        "id": "........",
        "variables": {
            "city": "Чита",
            "friends_number": "0"
        }
    },
    input="Куда пойти вечером? Где понюхать багульник?",
)

print(response.output_text)