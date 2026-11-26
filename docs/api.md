# API версии 2

Живой контракт: `http://localhost:8000/docs`; сохранённая схема: [openapi.json](openapi.json). Все пути ниже указаны без frontend-префикса `/api`.

| Группа | Основные пути |
| --- | --- |
| Вход | `POST /auth/register`, `/auth/login`, `/auth/logout` |
| Профиль | `GET/PUT /me`, `GET /users/{id}` |
| Каталог | `GET /projects`, `/projects/{id}`, `/stats` |
| Проекты автора | `POST /projects`, `PUT /projects/{id}`, `GET /me/projects` |
| Набор | `POST /projects/{id}/recruitment` с `{"open":true/false}`; `/close` оставлен как короткое закрытие |
| Команда | `GET /me/teams`, `DELETE /projects/{id}/members/{user_id}` |
| Отклики | `POST /vacancies/{id}/applications`, `GET /me/applications`, `/projects/{id}/applications` |
| Решение/отзыв | `POST /applications/{id}/decision`, `/applications/{id}/withdraw` |
| Модерация | `GET /moderation/projects`, `POST /moderation/projects/{id}` |
| Жалобы | `POST /reports`, `GET /me/reports`, `/moderation/reports`, `POST /moderation/reports/{id}` |
| Ограничения | `GET /moderation/users`, `POST /moderation/users/{id}/block` |
| История | `GET /moderation/history?page=1`, `/me/notices` |

Авторизация: `Authorization: Bearer <access_token>`. Регистрация и вход возвращают токен, срок действия и его тип. Токен не передаётся через URL.

Фильтры каталога: `q`, `category`, `format`, `skill`, `open_only`, `page`. По 12 карточек, подсчёт и пагинация выполняются в БД. Отсутствующий/недоступный проект возвращает 404. Ошибки содержат `detail`, ошибки проверки полей дополнительно `errors`.

Поля `moderation_note` и `team_contact` для посторонних возвращаются пустыми строками. Жалобы доступны только заявителю и модераторам; публичного списка заявителей нет.

Все правила и состояния: [FORDEV.md](../FORDEV.md).
