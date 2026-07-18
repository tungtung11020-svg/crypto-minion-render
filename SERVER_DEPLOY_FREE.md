# Бесплатный сервер: Render + Neon

1. Создайте бесплатную PostgreSQL-базу в Neon и скопируйте connection string.
2. Не добавляйте `.env` и `data/licensing.db` в GitHub.
3. Загрузите проект в приватный GitHub-репозиторий.
4. В Render выберите New → Blueprint и подключите репозиторий.
5. Заполните секретные переменные из локального `.env`; для DATABASE_URL используйте строку Neon.
6. После первого deploy установите API_PUBLIC_URL равным HTTPS-адресу Render.
7. Проверьте `/v1/health`.
8. В UptimeRobot добавьте HTTPS monitor на `/v1/health` с интервалом 5 минут.

Локальная SQLite продолжает работать. На сервере используется Neon PostgreSQL.
Никогда не публикуйте BOT_TOKEN, SERVER_PEPPER, приватный Ed25519-ключ или `.env`.
