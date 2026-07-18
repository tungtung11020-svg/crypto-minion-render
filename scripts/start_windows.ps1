$ErrorActionPreference = "Stop"
if (!(Test-Path .venv)) { py -3.12 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env; python scripts\generate_secrets.py; Write-Host "Заполните BOT_TOKEN и ADMIN_IDS в .env"; exit 0 }
alembic upgrade head
python scripts\seed_plans.py
python start.py
