# Multilingual Videos

Платформа перевода видео на базе SeamlessM4T.

## Запуск

```bash
mkdir -p .envs
cp .envs_examples/.app .envs/.app
cp .envs_examples/.db .envs/.db
docker compose up --build
```

Фронтенд будет доступен на `http://localhost:5173`, Swagger API на `http://localhost:8888/docs`.

## API

- `POST /videos/?source_lang=eng&target_lang=rus` - загрузить видео и создать задачу.
- `GET /videos/{task_id}` - получить статус задачи.
- `GET /videos/{task_id}/download` - скачать результат, если задача завершилась успешно.

Языки задаются кодами SeamlessM4T, например `eng`, `deu`, `rus`.
