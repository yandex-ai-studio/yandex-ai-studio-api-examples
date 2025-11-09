import openai
import numpy as np
from typing import List, Literal

# Конфигурация
YANDEX_CLOUD_FOLDER = "..."
YANDEX_CLOUD_API_KEY = "..."

MODELS = {
    "doc": "text-search-doc/latest",
    "query": "text-search-query/latest"
}

# Инициализация клиента
client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    project=YANDEX_CLOUD_FOLDER,
    base_url="https://llm.api.cloud.yandex.net/v1",
)

# Данные
DOC_TEXTS = [
    """Александр Сергеевич Пушкин (26 мая [6 июня] 1799, Москва — 29 января [10 февраля] 1837, Санкт-Петербург) — русский поэт, драматург и прозаик, заложивший основы русского реалистического направления, литературный критик и теоретик литературы, историк, публицист, журналист.""",
    """Ромашка — род однолетних цветковых растений семейства астровые, или сложноцветные, по современной классификации объединяет около 70 видов невысоких пахучих трав, цветущих с первого года жизни."""
]
QUERY_TEXT = "когда день рождения Пушкина?"


def get_embedding(text: str, text_type: Literal["doc", "query"] = "doc") -> np.ndarray:
    """Получает эмбеддинг для текста."""
    model_uri = f"emb://{YANDEX_CLOUD_FOLDER}/{MODELS[text_type]}"
    print(model_uri)
    response = client.embeddings.create(
        model=model_uri,
        input=text,
        encoding_format="float"
    )
    return np.array(response.data[0].embedding)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Вычисляет косинусное сходство между двумя векторами."""
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def find_most_similar(query: str, documents: List[str]) -> tuple[str, float]:
    """Находит наиболее похожий документ на запрос."""
    # Получаем эмбеддинг запроса
    query_emb = get_embedding(query, text_type="query")

    # Получаем эмбеддинги документов
    docs_embs = [get_embedding(doc, text_type="doc") for doc in documents]

    # Вычисляем сходство
    similarities = [cosine_similarity(query_emb, doc_emb) for doc_emb in docs_embs]

    # Находим максимальное сходство
    max_idx = np.argmax(similarities)

    return documents[max_idx], similarities[max_idx]


if __name__ == "__main__":
    most_similar_doc, similarity = find_most_similar(QUERY_TEXT, DOC_TEXTS)

    print(f"Запрос: {QUERY_TEXT}\n")
    print(f"Наиболее релевантный документ (сходство: {similarity:.4f}):\n")
    print(most_similar_doc)
