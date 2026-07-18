import hashlib,secrets
from desktop_client.token_storage import SecureStorage
APP_ID='crypto-minion-desktop-v1'; APP_SALT='km-local-device-salt-v1'
def get_device_id()->str:
    store=SecureStorage('identity.bin'); installation=store.load_text()
    if not installation: installation=secrets.token_hex(32); store.save_text(installation)
    return hashlib.sha256(f'{installation}:{APP_ID}:{APP_SALT}'.encode()).hexdigest()
