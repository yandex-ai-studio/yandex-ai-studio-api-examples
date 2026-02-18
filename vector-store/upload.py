import pathlib
from openai import OpenAI

YANDEX_API_KEY = "<API-ключ>"
YANDEX_FOLDER_ID = "<идентификатор_каталога>"


# Локальный файл для индексации
def local_path(path: str) -> pathlib.Path:
    return pathlib.Path(__file__).parent / path


def main():
    client = OpenAI(
        api_key=YANDEX_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        project=YANDEX_FOLDER_ID,
    )

    # Загружаем несколько файлов
    file_names = ["bali.md", "kazakhstan.md"]
    file_ids = []

    print("Загружаем файлы...")
    for fname in file_names:
        f = client.files.create(
            file=open(local_path(fname), "rb"),
            # Значение assistants используется для всех файлов, которые должны подключаться
            # к Vector Store API
            purpose="assistants",
        )
        print(f"Файл {fname} загружен:", f.id)
        file_ids.append(f.id)


if __name__ == "__main__":
    main()
