import openai

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)

# Создаём стриминговый запрос
with client.responses.stream(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        input="Напиши короткий тост на день рождения, дружелюбный и смешной."
) as stream:
    for event in stream:
        # Дельты текстового ответа
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
        # Событие, показывающее, что ответ завершен
        # elif event.type == "response.completed":
        #     print("\n---\nОтвет завершён")

    # При необходимости можно забрать текст ответа целиком
    # final_response = stream.get_final_response()
    # print("\nПолный текст ответа:\n", final_response.output_text)
