import time
from openai import OpenAI

YANDEX_API_KEY = "<API-ключ>"
YANDEX_FOLDER_ID = "<идентификатор_каталога>"


def main():
    client = OpenAI(
        api_key=YANDEX_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        project=YANDEX_FOLDER_ID,
    )

    input_file_ids = ["<идентификатор_файла_1>", "<идентификатор_файла_2>"]

    # Создаем поисковый индекс с несколькими файлами
    print("Создаем поисковый индекс...")
    vector_store = client.vector_stores.create(
        # Говорящее название индекса
        name="База знаний поддержки",
        # Ваши метки для файлов
        metadata={"key": "value"},
        # Время жизни индекса
        # last_active_at - после последней активности
        expires_after={"anchor": "last_active_at", "days": 1},
        # или created_at - после создания
        # expires_after={"anchor": "created_at", "days": 1},
        file_ids=input_file_ids,  # <- список файлов
    )
    vector_store_id = vector_store.id
    print("Vector store:", vector_store_id)

    # Ждем готовности поискового индекса
    while True:
        vector_store = client.vector_stores.retrieve(vector_store_id)
        print("Статус vector store:", vector_store.status)
        # in_progress — индекс строится (файлы загружаются, делятся на фрагменты, считаются эмбеддинги)
        # completed — все готово, можно искать
        # failed — что-то пошло не так при построении индекса
        if vector_store.status == "completed":
            break
        time.sleep(2)

    print("Vector store готов к работе.")


if __name__ == "__main__":
    main()
