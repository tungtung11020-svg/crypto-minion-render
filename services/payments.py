from abc import ABC,abstractmethod
from dataclasses import dataclass
@dataclass(frozen=True)
class Invoice: title:str; description:str; payload:str; currency:str; amount:int
class PaymentProvider(ABC):
    @abstractmethod
    async def send_invoice(self,bot,chat_id:int,invoice:Invoice): ...
class TelegramStarsProvider(PaymentProvider):
    async def send_invoice(self,bot,chat_id:int,invoice:Invoice):
        from aiogram.types import LabeledPrice
        return await bot.send_invoice(chat_id=chat_id,title=invoice.title,description=invoice.description,payload=invoice.payload,currency='XTR',prices=[LabeledPrice(label=invoice.title,amount=invoice.amount)])
class TestPaymentProvider(PaymentProvider):
    async def send_invoice(self,bot,chat_id:int,invoice:Invoice):
        return await bot.send_message(chat_id,f'ТЕСТОВЫЙ РЕЖИМ. Заказ {invoice.payload}\nДля подтверждения администратор использует /test_pay {invoice.payload}')
