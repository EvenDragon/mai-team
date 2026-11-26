# Backend

FastAPI + SQLAlchemy + PostgreSQL. Основное объяснение — [FORDEV.md](../FORDEV.md).

`app/main.py` подключает маршруты из `app/routers`, обработчики ошибок и общие заголовки. `models.py` описывает таблицы, `schemas.py` — контракт запросов и ответов. `security.py` проверяет сессии, `services.py` содержит общие проверки и пакетную сборку ответов.

Из корня установи зависимости в виртуальное окружение: `python -m pip install -r backend/requirements.lock.txt` (в активированной `.venv`). Укажи `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/mai`.

Из папки `backend`:

```text
python -m app.migrate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
python -m pytest tests -q
```

`/docs` — интерактивное описание API. `app.seed` загружает демо только при `ALLOW_DEMO_SEED=true`. Приложение само не создаёт таблицы при старте; сначала выполняются SQL-миграции.

Полные тесты требуют `TEST_DATABASE_URL` на отдельную БД с суффиксом `_test` и `ALLOW_TEST_DB_RESET=true`: её схема очищается перед проверками. Без этой переменной используется SQLite, тесты PostgreSQL пропускаются.
