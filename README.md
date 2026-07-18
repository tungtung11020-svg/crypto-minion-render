# Крипто Миньон — лицензирование

Production-oriented MVP Telegram-бота, API активации и PyQt6-модуля. **Крипто Миньон — игровая симуляция. Все отображаемые кошельки, находки и балансы являются вымышленными. Виртуальный баланс не является реальными денежными средствами и не подлежит выводу.**

## Быстрый запуск Windows PowerShell
1. Установите Python 3.12 с python.org и отметьте **Add Python to PATH**.
2. Создайте бота у `@BotFather` командой `/newbot`, сохраните `BOT_TOKEN`.
3. Узнайте свой Telegram ID у `@userinfobot` и внесите в `ADMIN_IDS`.
4. Выполните:
```powershell
cd crypto_minion_licensing
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\generate_secrets.py
notepad .env
alembic upgrade head
python scripts\seed_plans.py
pytest -q
python start.py
```
Заполните `BOT_TOKEN`, `BOT_USERNAME`, `ADMIN_IDS`, ссылки и URL API. Локальная документация: `http://127.0.0.1:8000/docs`. Здоровье: `/v1/health`.

Отдельно API: `uvicorn api.main:app --host 127.0.0.1 --port 8000`. Отдельно бот: `python -m bot.main`.

## Оплата
Для цифровых товаров внутри Telegram официальный путь — Telegram Stars (`XTR`), см. https://core.telegram.org/bots/payments-stars. В live-режиме установите `PAYMENT_MODE=stars`; provider token для Stars пуст. Тестовый режим проекта (`PAYMENT_MODE=test`) не создаёт реальную оплату и предназначен для разработки. Никогда не выдавайте ключ по скриншоту или сообщению.

## Миграции и планы
Перед каждой миграцией: `python scripts\backup_database.py`, затем `alembic upgrade head`. Начальные планы загружаются `python scripts\seed_plans.py` и хранятся в БД.

## Backup и восстановление
```powershell
python scripts\backup_database.py
python scripts\restore_database.py data\backups\licensing_YYYYMMDD_HHMMSS.db --confirm ВОССТАНОВИТЬ
```
Хранятся 7 последних копий. `.env` и приватные ключи в backup не включаются. Для защиты от поломки диска вручную копируйте зашифрованный backup на другой носитель.

## PyQt6-интеграция
Скопируйте папку `desktop_client` в корень существующего проекта, не заменяя изображения и фирменные ассеты. Скопируйте `core/security.py` либо вынесите проверку token в общий пакет. До показа главного окна добавьте:
```python
from desktop_client.integration_example import ensure_activated
if not ensure_activated(API_URL, f"https://t.me/{BOT_USERNAME}", ED25519_PUBLIC_KEY):
    raise SystemExit(0)
main_window = MainWindow()
main_window.show()
```
В EXE помещается **только** `ED25519_PUBLIC_KEY`. Никогда не включайте `SERVER_PEPPER` и приватный ключ. Онлайн-валидацию вызывайте при старте и каждые 24 часа; offline token действует 72 часа. Сборка:
```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name CryptoMinion your_main.py
```
DPAPI используется на Windows. Fallback-файл с правами пользователя менее безопасен.

## Бесплатное размещение
На 17.07.2026 Telegram официально требует Stars для цифровых товаров. Для API можно проверить FastAPI Cloud Hobby (public beta, заявляет старт без карты) либо Koyeb, где заявлен автоматический HTTPS. Условия, сон инстанса и наличие постоянного диска меняются: проверьте pricing/terms в день развёртывания. SQLite требует **постоянного volume**; если бесплатный тариф его не даёт, база исчезнет при redeploy. Поэтому единственный гарантированно бесплатный вариант — запуск на компьютере владельца; для публичного HTTPS можно использовать бесплатный tunnel только после проверки его условий. Не обещайте доступность 24/7.

Пример cloud-команды: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`. Секреты задайте в панели хостинга, не коммитьте `.env`. Технический поддомен и HTTPS должны выдаваться платформой.

## Перенос на другой компьютер
Остановите процессы, сделайте backup, скопируйте проект без `.venv`, безопасно перенесите `.env` отдельно, создайте новую venv, установите зависимости, восстановите БД и запустите тесты. Потеря pepper сделает старые ключи недоступными; потеря Ed25519 private key не позволит выпускать новые token.

## Администрирование
Команды: `/stats`, `/orders`, `/payments`, `/plans`, `/activation_log`, `/backup`, `/license LAST4`, `/block LICENSE_UUID`, `/unblock LICENSE_UUID`, `/revoke LICENSE_UUID`, `/reset_devices LICENSE_UUID`, `/resend LICENSE_UUID`, `/refund LICENSE_UUID`, `/test_pay PAYLOAD`. Опасные действия подтверждаются кнопкой и пишутся в `admin_actions`. Возврат выполняйте только после подтверждения платёжным провайдером. Для повторной доставки ключ хранится не открыто, а в AES-GCM ciphertext, ключ шифрования выводится из серверного pepper. Это компромисс между повторной доставкой и минимизацией хранения; удаление ciphertext после подтверждённой доставки усилит безопасность, но отключит `/resend`.

## Ограничения
SQLite подходит для одного процесса/узла и небольшой нагрузки. Rate limiting SQLite не защищает от распределённого ботнета. Desktop-клиент под контролем пользователя: защитить локальную игровую статистику абсолютно невозможно; сервер может лишь проверять события, уникальность и аномалии. Перед коммерческим запуском нужны юридическая проверка условий/возвратов и тестирование на Windows.

## Расходы
| Компонент | Обязательная стоимость |
|---|---:|
| Создание Telegram-бота | 0 ₽ |
| Python | 0 ₽ |
| Python-библиотеки | 0 ₽ |
| SQLite | 0 ₽ |
| Локальный запуск | 0 ₽ |
| Тестирование платежей | 0 ₽ |
| Лицензионные ключи | 0 ₽ |
| Локальный API | 0 ₽ |
| Резервные копии | 0 ₽ |
| **Итог для MVP** | **0 ₽** |

Необязательные будущие расходы: VPS, домен, комиссии платёжной системы, профессиональная техническая поддержка. Они не требуются для локального MVP.
