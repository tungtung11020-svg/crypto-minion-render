import asyncio
from PyQt6.QtCore import QThread,pyqtSignal
from PyQt6.QtWidgets import QDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QProgressBar,QPushButton,QVBoxLayout
from desktop_client.activation_client import ActivationClient
from desktop_client.device_identity import get_device_id
from desktop_client.token_storage import SecureStorage
class Worker(QThread):
    done=pyqtSignal(dict); failed=pyqtSignal(str)
    def __init__(self,url,key): super().__init__(); self.url=url; self.key=key
    def run(self):
        try: self.done.emit(asyncio.run(ActivationClient(self.url).activate(self.key,get_device_id())))
        except Exception as e: self.failed.emit(str(e))
class ActivationDialog(QDialog):
    def __init__(self,api_url,bot_url,parent=None):
        super().__init__(parent); self.api_url=api_url; self.bot_url=bot_url; self.setWindowTitle('Активация — Крипто Миньон'); self.resize(520,260)
        layout=QVBoxLayout(self); layout.addWidget(QLabel('<b>Введите лицензионный ключ</b>'))
        self.key=QLineEdit(); self.key.setPlaceholderText('KM-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX'); self.key.textChanged.connect(self.format_key); layout.addWidget(self.key)
        buttons=QHBoxLayout(); self.activate_btn=QPushButton('Активировать'); self.paste_btn=QPushButton('Вставить'); self.buy_btn=QPushButton('Купить ключ'); buttons.addWidget(self.activate_btn); buttons.addWidget(self.paste_btn); buttons.addWidget(self.buy_btn); layout.addLayout(buttons)
        self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); layout.addWidget(self.progress); self.status=QLabel('Крипто Миньон — игровая симуляция. Все балансы вымышлены, вывод недоступен.'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.activate_btn.clicked.connect(self.activate); self.paste_btn.clicked.connect(lambda:self.key.setText(__import__('PyQt6').QtWidgets.QApplication.clipboard().text())); self.buy_btn.clicked.connect(lambda:__import__('PyQt6').QtGui.QDesktopServices.openUrl(__import__('PyQt6').QtCore.QUrl(bot_url)))
    def format_key(self,text):
        raw=text.upper().replace(' ','').replace('-',''); raw=raw[2:] if raw.startswith('KM') else raw; formatted='KM-'+'-'.join(raw[i:i+4] for i in range(0,min(len(raw),32),4));
        if formatted!=text: self.key.blockSignals(True); self.key.setText(formatted); self.key.blockSignals(False)
    def activate(self):
        self.progress.show(); self.activate_btn.setEnabled(False); self.worker=Worker(self.api_url,self.key.text()); self.worker.done.connect(self.success); self.worker.failed.connect(self.failure); self.worker.start()
    def success(self,data): SecureStorage('activation.token').save_text(data['activation_token']); self.accept()
    def failure(self,msg): self.progress.hide(); self.activate_btn.setEnabled(True); self.status.setText(msg)
