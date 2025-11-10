# Yandex AI Studio API Examples

Yandex AI Studio — это платформа для создания AI-агентов и ИИ-приложений.
Этот репозиторий создан, чтобы показать, как начать работать с API AI Studio — от простых запросов к модели до создания голосовых агентов и систем с памятью и поиском.

```
yandex-ai-studio-api-examples/
├── responses/ # Примеры работы с Responses API
│ ├── background.py # Запуск в background режиме
│ ├── dialog.py # Простой диалог с использование previous_request_id
│ ├── file_search_tool.py # Использование file_search инструмента
│ ├── function_calling.py # Пример использования function calling
│ ├── id_variables.py # Пример использования id конфигурации диалога, созданного в консоли
│ ├── mcp_always_approve.py # mcp tool без подтверждения
│ ├── mcp_submit_approve.py # mcp tool с подтвеждением
│ ├── simple_request.py # Обращение к модели
│ ├── stream.py # Генерация с промежуточными результатами
│ └── web_tool.py # Использование web_search инструмента
├── realtime/ # Примеры голосовых агентов (WebSocket)
│ ├── voice-agent.py # Голосовой агент с реализацией поверх API
│ ├── to do # Голосовой агент с реализацией поверх SDK
│ └── to do
├── embeddings/ # Примеры получения эмбеддингов
│ └── embeddings.py # Пример работы с эмбеддингами
├── vector_store/ # Примеры загрузки и поиска в векторном хранилище
│ ├── index.py # Создании индекса из загруженных файлов
│ ├── upload.py # Загрузка файлов
│ └── to do
├── tuning/ # Примеры тонкой настройки моделей
│ └── to do
└── README.md
```

## Полезные ссылки

- [Документация Yandex AI Studio](https://yandex.cloud/ru/docs/ai-studio/)
- [Пошаговые инструкции](https://yandex.cloud/ru/docs/ai-studio/operations/)
- [Model Gallery](https://yandex.cloud/ru/docs/ai-studio/concepts/generation/)
- [Yandex Cloud Community](https://t.me/YFM_Community)
