import openai
import json

YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."
YANDEX_CLOUD_MODEL = "yandexgpt"

# Определение MCP tools
MCP_TOOLS = [
    {
        "type": "mcp",
        "server_label": "kontur",
        "server_description": "Возвращает информацию по ИНН",
        "server_url": "...", # URL MCP
        "require_approval": "always"
    },
]

# Вывод информации о запросе на подтверждение
def print_approval_request(req):
    print(f"ID: {req.get('id')}")
    print(f"Server: {req.get('server_label')}")
    print(f"Tool: {req.get('name')}")
    print(f"Arguments: {req.get('arguments')}")
    print("-" * 50)

# Извлечение запросов на подтверждение из ответа
def get_approval_requests(response_dict):
    approval_requests = []
    if "output" in response_dict:
        for item in response_dict.get("output", []):
            if item.get("type") == "mcp_approval_request":
                approval_requests.append(item)
    return approval_requests


# Подтверждаем запросы
def create_approval_responses(approval_requests):
    return [
        {
            "type": "mcp_approval_response",
            "approve": True,
            "approval_request_id": req.get('id')
        }
        for req in approval_requests
    ]


def main():
    # Инициализация клиента
    client = openai.OpenAI(
        api_key=YANDEX_CLOUD_API_KEY,
        project=YANDEX_CLOUD_FOLDER,
        base_url="https://ai.api.cloud.yandex.net/v1",
    )

    # Первый запрос
    response = client.responses.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        tools=MCP_TOOLS,
        input="чей инн 561100409545",
    )

    response_dict = response.model_dump()
    approval_requests = get_approval_requests(response_dict)

    if approval_requests:
        print("Обнаружены запросы на подтверждение:")
        print("=" * 50)

        prev_message_id = response_dict.get('id')
        print(f"Previous Response ID: {prev_message_id}\n")

        for req in approval_requests:
            print_approval_request(req)

        # Запрос с подтверждением
        user_approval = input("\nПодтвердить выполнение запроса? (yes/no): ").strip().lower()

        if user_approval == "yes":
            input_items = create_approval_responses(approval_requests)

            print("\nОтправляем подтверждение:")
            print(json.dumps(input_items, indent=2, ensure_ascii=False))


            # Повторный запрос с одобренными инструментами
            response = client.responses.create(
                model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
                tools=MCP_TOOLS,
                previous_response_id=prev_message_id,
                input=input_items
            )

            print("\n" + "=" * 50)
            print("Результат после подтверждения:")
            print("\nТекст ответа:")
            print(response.output_text)
        else:
            print("\nЗапрос отклонен пользователем.")
            return
    else:
        print("\nТекст ответа:")
        print(response.output_text)

    print("\n" + "=" * 50 + "\n")
    print("Полный ответ (JSON):")
    print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
