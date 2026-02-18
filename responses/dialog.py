import openai

YANDEX_CLOUD_FOLDER_ID = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "..."

previous_id = None  # храним ID последнего ответа ассистента

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    project=YANDEX_CLOUD_FOLDER_ID,
    base_url="https://ai.api.cloud.yandex.net/v1",
)

print("Чат с агентом (введите 'выход' для выхода)\n")

while True:
    user_input = input("Вы: ")
    if user_input.lower() in ("exit", "quit", "выход"):
        print("Чат завершён.")
        break

    response = client.responses.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER_ID}/{YANDEX_CLOUD_MODEL}",
        input=user_input,
        instructions="Ты — текстовый агент, который ведёт диалог и даёт информативные ответы на вопросы пользователя.",
        previous_response_id=previous_id  # передаём контекст, если он есть
    )

    # сохраняем ID для следующего шага
    previous_id = response.id

    # выводим ответ агента
    print("Агент:", response.output_text)
