from PyQt6.QtWidgets import QLabel,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
class PersonalAccount(QWidget):
    def __init__(self,license_data:dict,balance='0',history=None):
        super().__init__(); history=history or []; l=QVBoxLayout(self); l.addWidget(QLabel('<h2>Личный кабинет</h2>'))
        l.addWidget(QLabel(f"Ключ: {license_data.get('masked_key','—')}\nТариф: {license_data.get('plan','—')}\nСтатус: активна\nСрок: {license_data.get('expires_at') or 'бессрочно'}\nУстройства: {license_data.get('devices','—')}\nФункции: {', '.join(license_data.get('features',[]))}"))
        l.addWidget(QLabel(f'<b>Игровой баланс: {balance}</b><br>Игровая симуляция — не реальные средства. Вывод недоступен.'))
        table=QTableWidget(len(history),3); table.setHorizontalHeaderLabels(['Дата','Событие','Виртуальная сумма'])
        for r,item in enumerate(history):
            for c,key in enumerate(('created_at','event_type','amount')): table.setItem(r,c,QTableWidgetItem(str(item.get(key,''))))
        l.addWidget(table)
