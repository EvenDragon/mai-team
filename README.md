# МАИ.Команда

Сервис для поиска студенческих проектов и формирования команд: каталог, роли, отклики, состав команды, Telegram-контакт, модерация и жалобы.

**Стек:** FastAPI + SQLAlchemy + PostgreSQL, React + JavaScript + Vite, обычный CSS.

## Начать здесь

- [FORDEV.md](FORDEV.md) — понятное описание всех частей, логики, базы и запуска.
- На подготовленном Windows-компьютере: `START.cmd`, затем http://127.0.0.1:3000. Остановка: `STOP.cmd`.
- [Результаты проверок](docs/verification.md).

## Запуск через Docker

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d --wait
```

Перед запуском открой Docker Desktop и дождись готовности движка Linux containers. В `.env` задай свой `POSTGRES_PASSWORD` (буквы и цифры). Если работает локальная версия через `START.cmd`, сначала останови её через `STOP.cmd`: они используют одинаковые порты.

Сайт: http://localhost:3000. API: http://localhost:8000/docs. В Docker создаётся отдельная база в томе `mai-team_pgdata`; существующая локальная база автоматически не переносится. Остановка с сохранением данных: `docker compose down`. Состояние: `docker compose ps -a`, логи: `docker compose logs --tail 100`.
Демо-данные отключены по умолчанию. Для отдельной демобазы выстави `ALLOW_DEMO_SEED=true`, затем `docker compose --profile demo run --rm seed`.

Демо-аккаунты: `author@example.com`, `student@example.com`, `moderator@example.com`, `member@example.com`. Пароль: `DemoTeam2026!`. Это вымышленные данные только для локальной проверки.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
docker compose --profile test run --rm test
```

Первая команда использует SQLite для быстрых проверок. Вторая — изолированную PostgreSQL. Рабочая база всегда PostgreSQL. Сборка интерфейса из `frontend`: `pnpm build`.

## Состояние

Переработка находится в локальной ветке `feature/service-rework`. Изменения не отправлены в GitHub и не развёрнуты. Окружение, пароли и данные `.local` не входят в репозиторий.
