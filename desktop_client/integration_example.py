# Скопируйте папку desktop_client в корень существующего проекта.
# В вашей точке входа создайте QApplication, затем выполните этот код ДО main_window.show().
from PyQt6.QtWidgets import QApplication,QMessageBox
from desktop_client.activation_dialog import ActivationDialog
from desktop_client.device_identity import get_device_id
from desktop_client.token_storage import SecureStorage
from core.security import verify_activation_token

def ensure_activated(api_url:str,bot_url:str,public_key_b64:str)->bool:
    token=SecureStorage('activation.token').load_text()
    if token:
        try: verify_activation_token(token,public_key_b64,get_device_id()); return True
        except ValueError: pass
    dialog=ActivationDialog(api_url,bot_url)
    return dialog.exec()==dialog.DialogCode.Accepted
# if not ensure_activated(API_URL, BOT_URL, ED25519_PUBLIC_KEY): sys.exit(0)
# main_window = MainWindow(); main_window.show()
