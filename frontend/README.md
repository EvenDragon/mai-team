# Frontend

React + JavaScript + Vite. React Router отвечает за адреса страниц. CSS обычный, без Tailwind. Нет Next.js, TypeScript и Redux.

```text
pnpm install --frozen-lockfile
pnpm dev
pnpm build
pnpm format
```

Запускай команды из этой папки. Node.js 22.12+; проверено на Node.js 24. Для Windows при необходимости используй `pnpm.cmd` вместо `pnpm`.

Vite открывает http://127.0.0.1:3000 и отправляет `/api` на `127.0.0.1:8000`. FastAPI нужно запустить отдельно. `API_PROXY_TARGET` меняет адрес API для разработки. `VITE_API_URL` нужен только при намеренном размещении API на отдельном адресе, по умолчанию используется `/api`.

Сборка попадает в `dist`. Контейнер раздаёт её через nginx и проксирует API. Прямые ссылки на страницы работают благодаря fallback на `index.html`. `pnpm preview` — просмотр сборки; без настроенного прокси API это не полный запуск сервиса.

Карта файлов и примеры логики — в [FORDEV.md](../FORDEV.md).
