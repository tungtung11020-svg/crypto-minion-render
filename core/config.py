from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file='.env', extra='ignore')
    bot_token: str=''
    bot_username: str=''
    admin_ids: str=''
    database_url: str='sqlite+aiosqlite:///./data/licensing.db'
    server_pepper: str=''
    ed25519_private_key: str=''
    ed25519_public_key: str=''
    payment_mode: str='test'
    payment_provider_token: str=''
    app_download_url: str='https://example.invalid'
    support_url: str='https://t.me/example'
    api_public_url: str='http://127.0.0.1:8000'
    api_host: str='127.0.0.1'
    api_port: int=8000
    offline_grace_hours: int=72
    rate_limit_attempts: int=8
    rate_limit_window_seconds: int=900
    rate_limit_block_seconds: int=1800
    @property
    def admin_id_set(self)->set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(',') if x.strip()}
    def validate_secrets(self)->None:
        if not self.server_pepper or not self.ed25519_private_key or not self.ed25519_public_key:
            raise RuntimeError('Сначала выполните scripts/generate_secrets.py и заполните .env')
@lru_cache
def get_settings()->Settings: return Settings()
