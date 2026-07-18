import asyncio,json,logging
from aiogram import Bot,Dispatcher,F,Router
from aiogram.filters import Command,CommandObject
from aiogram.types import CallbackQuery,Message,PreCheckoutQuery
from sqlalchemy import func,select
from bot.admin_panel import admin_panel_router
from bot.admin_license_controls import admin_license_router
from bot.admin_panel import admin_panel_router
from bot.keyboards import (TERMS_URL,about_keyboard,back_home_keyboard,confirm_keyboard,download_keyboard,
    home_keyboard,licenses_keyboard,main_menu,plan_actions,plans_keyboard,support_keyboard)
from bot.ui import (about_text,guide_text,licenses_text,plan_card,
    plans_text,terms_text,welcome_text)
from core.config import get_settings
from core.license_keys import mask_key
from core.security import decrypt_delivery_secret
from database.backup import backup_database_async
from database.models import AdminAction,License,Order,Payment,Plan,TelegramUser
from database.session import SessionLocal
from services.licensing import PaymentError,create_order,process_successful_payment
from services.payments import Invoice,TelegramStarsProvider,TestPaymentProvider
router=Router(); cfg=get_settings()
def is_admin(uid): return uid in cfg.admin_id_set
async def active_plans():
    async with SessionLocal() as s: return list((await s.execute(select(Plan).where(Plan.is_active==True).order_by(Plan.price))).scalars())
@router.message(Command('start'))
async def start(m:Message):
    await m.answer(welcome_text(m.from_user.first_name),reply_markup=home_keyboard())

@router.message(Command('menu'))
async def menu(m:Message):
    await m.answer(welcome_text(m.from_user.first_name),reply_markup=home_keyboard())

LICENSES_PAGE_SIZE=2

async def license_rows(telegram_id:int,page:int=0):
    async with SessionLocal() as s:
        total=(await s.execute(select(func.count()).select_from(License).where(License.purchaser_telegram_id==telegram_id))).scalar_one()
        total_pages=max(1,(total+LICENSES_PAGE_SIZE-1)//LICENSES_PAGE_SIZE)
        page=max(0,min(page,total_pages-1))
        query=(
            select(License,Plan)
            .join(Plan)
            .where(License.purchaser_telegram_id==telegram_id)
            .order_by(License.created_at.desc(),License.updated_at.desc(),License.id.desc())
            .offset(page*LICENSES_PAGE_SIZE)
            .limit(LICENSES_PAGE_SIZE)
        )
        rows=(await s.execute(query)).all()
        prepared=[(l,p,decrypt_delivery_secret(l.key_delivery_ciphertext,cfg.server_pepper) if l.key_delivery_ciphertext else mask_key(l.key_last4)) for l,p in rows]
        return prepared,page,total_pages,total
@router.callback_query(F.data=='ui:home')
async def ui_home(c:CallbackQuery):
    await c.message.edit_text(welcome_text(c.from_user.first_name),reply_markup=home_keyboard()); await c.answer()

@router.callback_query(F.data=='ui:plans')
async def ui_plans(c:CallbackQuery):
    await c.message.edit_text(plans_text(),reply_markup=plans_keyboard(await active_plans())); await c.answer()

@router.callback_query(F.data.startswith('plan:'))
async def ui_plan(c:CallbackQuery):
    plan_id=c.data.split(':',1)[1]
    async with SessionLocal() as s: plan=await s.get(Plan,plan_id)
    if not plan or not plan.is_active: return await c.answer('Тариф сейчас недоступен',show_alert=True)
    await c.message.edit_text(plan_card(plan),reply_markup=plan_actions(plan.id)); await c.answer()

@router.callback_query(F.data.startswith('ui:licenses'))
async def ui_licenses(c:CallbackQuery):
    parts=c.data.split(':')
    try: requested_page=int(parts[2]) if len(parts)>2 else 0
    except (TypeError,ValueError): requested_page=0
    rows,page,total_pages,total=await license_rows(c.from_user.id,requested_page)
    text=licenses_text(rows)
    if total:
        text+=f'\n\n<code>Страница {page+1} из {total_pages}  ·  Всего лицензий: {total}</code>'
    try:
        await c.message.edit_text(text,reply_markup=licenses_keyboard(bool(rows),page,total_pages))
    except Exception as error:
        if 'message is not modified' not in str(error).lower(): raise
    await c.answer()
@router.callback_query(F.data=='ui:guide')
async def ui_guide(c:CallbackQuery):
    await c.message.edit_text(guide_text(),reply_markup=back_home_keyboard()); await c.answer()

@router.callback_query(F.data=='ui:download')
async def ui_download(c:CallbackQuery):
    text='<b>◈  КРИПТО МИНЬОН</b>\n<code>СКАЧИВАНИЕ</code>\n\n🚀 <b>Установите приложение за пару минут</b>\nАктуальная версия уже готова — остаётся только загрузить и запустить.\n\n<b>01  📦 Загрузите приложение</b>\nНажмите кнопку ниже, чтобы получить последнюю версию.\n\n<b>02  🖥 Выполните установку</b>\nОткройте скачанный файл и следуйте подсказкам на экране.\n\n<b>03  🔑 Подготовьте лицензию</b>\nВаш ключ находится в разделе «Мои лицензии».\n\n<b>04  ✨ Запускайте</b>\nВставьте ключ в окно активации — и всё готово к работе.'
    await c.message.edit_text(text,reply_markup=download_keyboard(cfg.app_download_url)); await c.answer()
@router.callback_query(F.data=='ui:terms')
async def ui_terms(c:CallbackQuery):
    await c.answer('Условия находятся по ссылке в главном меню',show_alert=True)

@router.callback_query(F.data=='ui:support')
async def ui_support(c:CallbackQuery):
    text='<b>◈  КРИПТО МИНЬОН</b>\n<code>ПОДДЕРЖКА</code>\n\n💬 <b>Мы рядом, если что-то пошло не по плану</b>\nПоможем разобраться с покупкой, ключом, активацией или запуском приложения.\n\n<b>01  ✍️ Опишите вопрос</b>\nКоротко расскажите, что произошло и на каком этапе.\n\n<b>02  🧩 Добавьте детали</b>\nУкажите версию приложения и текст ошибки, если он появился.\n\n<b>03  📸 Прикрепите скриншот</b>\nТак мы быстрее увидим проблему и найдём решение.\n\n<b>04  ⚡ Получите помощь</b>\nНажмите кнопку ниже, чтобы открыть прямой чат с поддержкой.'
    await c.message.edit_text(text,reply_markup=support_keyboard(cfg.support_url)); await c.answer()
@router.callback_query(F.data=='ui:about')
async def ui_about(c:CallbackQuery):
    await c.message.edit_text(about_text(),reply_markup=about_keyboard()); await c.answer()

@router.message(F.text.in_({'Купить ключ','💎 Купить ключ'}))
async def buy(m:Message): await m.answer(plans_text(),reply_markup=plans_keyboard(await active_plans()))
@router.callback_query(F.data.startswith('buy:'))
async def choose(c:CallbackQuery):
    async with SessionLocal() as s:
        order=await create_order(s,c.from_user.id,c.from_user.username,c.from_user.full_name,c.data.split(':',1)[1]); plan=await s.get(Plan,order.plan_id)
    provider=TestPaymentProvider() if cfg.payment_mode=='test' else TelegramStarsProvider()
    await provider.send_invoice(c.bot,c.from_user.id,Invoice(plan.name,plan.description,order.invoice_payload,order.currency,order.amount)); await c.answer()
@router.pre_checkout_query()
async def precheckout(q:PreCheckoutQuery):
    async with SessionLocal() as s:
        order=(await s.execute(select(Order).where(Order.invoice_payload==q.invoice_payload))).scalar_one_or_none(); user=await s.get(TelegramUser,order.user_id) if order else None
        ok=bool(order and user and user.telegram_id==q.from_user.id and order.amount==q.total_amount and order.currency==q.currency and order.status=='pending')
    await q.answer(ok=ok,error_message=None if ok else 'Параметры заказа не совпадают')
@router.message(F.successful_payment)
async def paid(m:Message):
    p=m.successful_payment
    async with SessionLocal() as s:
        order=(await s.execute(select(Order).where(Order.invoice_payload==p.invoice_payload))).scalar_one_or_none()
        if not order: return await m.answer('Заказ не найден. Обратитесь в поддержку.')
        try: lic,key,duplicate=await process_successful_payment(s,order_id=order.id,tg_id=m.from_user.id,amount=p.total_amount,currency=p.currency,payload=p.invoice_payload,payment_id=p.telegram_payment_charge_id)
        except PaymentError: return await m.answer('Платёж не прошёл проверку. Обратитесь в поддержку.')
        plan=await s.get(Plan,lic.plan_id)
    if duplicate: return await m.answer('Этот платёж уже обработан. Лицензия доступна в «Мои лицензии».')
    expiry='бессрочно' if not plan.duration_days else f'{plan.duration_days} дней с '+('оплаты' if plan.starts_on=='payment' else 'первой активации')
    await m.answer(f'Оплата подтверждена.\n\nВаш лицензионный ключ:\n\n<code>{key}</code>\n\nТариф: {plan.name}\nКоличество устройств: {plan.max_devices}\nСрок действия: {expiry}\n\nСкопируйте ключ, откройте “Крипто Миньон” и вставьте его в окно активации.')
@router.message(F.text.in_({'Мои лицензии','🔑 Мои лицензии'}))
async def mine(m:Message):
    rows,page,total_pages,total=await license_rows(m.from_user.id,0)
    text=licenses_text(rows)
    if total:
        text+=f'\n\n<code>Страница {page+1} из {total_pages}  ·  Всего лицензий: {total}</code>'
    await m.answer(text,reply_markup=licenses_keyboard(bool(rows),page,total_pages))
@router.message(Command('test_pay'))
async def test_pay(m:Message,command:CommandObject):
    if not is_admin(m.from_user.id) or cfg.payment_mode!='test' or not command.args: return
    payload=command.args.strip()
    async with SessionLocal() as s:
        order=(await s.execute(select(Order).where(Order.invoice_payload==payload))).scalar_one_or_none()
        if not order: return await m.answer('Заказ не найден.')
        user=await s.get(TelegramUser,order.user_id); plan=await s.get(Plan,order.plan_id)
        try: lic,key,dup=await process_successful_payment(s,order_id=order.id,tg_id=user.telegram_id,amount=order.amount,currency=order.currency,payload=order.invoice_payload,payment_id='test:'+order.id)
        except PaymentError as e: return await m.answer(str(e))
    if not dup:
        await m.bot.send_message(user.telegram_id,f'Тестовая оплата подтверждена.\n\nВаш ключ:\n<code>{key}</code>')
    await m.answer('Тестовый платёж обработан.')
@router.message(F.text.in_({'Инструкция по активации','📖 Как активировать'}))
async def instruction(m): await m.answer(guide_text(),reply_markup=back_home_keyboard())
@router.message(F.text.in_({'Скачать приложение','📥 Скачать приложение'}))
async def download(m):
    text='<b>◈  КРИПТО МИНЬОН</b>\n<code>СКАЧИВАНИЕ</code>\n\n🚀 <b>Установите приложение за пару минут</b>\nАктуальная версия уже готова — остаётся только загрузить и запустить.\n\n<b>01  📦 Загрузите приложение</b>\nНажмите кнопку ниже, чтобы получить последнюю версию.\n\n<b>02  🖥 Выполните установку</b>\nОткройте скачанный файл и следуйте подсказкам на экране.\n\n<b>03  🔑 Подготовьте лицензию</b>\nВаш ключ находится в разделе «Мои лицензии».\n\n<b>04  ✨ Запускайте</b>\nВставьте ключ в окно активации — и всё готово к работе.'
    await m.answer(text,reply_markup=download_keyboard(cfg.app_download_url))
@router.message(F.text=='Условия использования')
async def terms(m): await m.answer(f'📜 <a href="{TERMS_URL}">Открыть условия использования</a>')
@router.message(F.text.in_({'Поддержка','💬 Поддержка'}))
async def support(m):
    text='<b>◈  КРИПТО МИНЬОН</b>\n<code>ПОДДЕРЖКА</code>\n\n💬 <b>Мы рядом, если что-то пошло не по плану</b>\nПоможем разобраться с покупкой, ключом, активацией или запуском приложения.\n\n<b>01  ✍️ Опишите вопрос</b>\nКоротко расскажите, что произошло и на каком этапе.\n\n<b>02  🧩 Добавьте детали</b>\nУкажите версию приложения и текст ошибки, если он появился.\n\n<b>03  📸 Прикрепите скриншот</b>\nТак мы быстрее увидим проблему и найдём решение.\n\n<b>04  ⚡ Получите помощь</b>\nНажмите кнопку ниже, чтобы открыть прямой чат с поддержкой.'
    await m.answer(text,reply_markup=support_keyboard(cfg.support_url))
@router.message(F.text.in_({'О программе','✨ О программе'}))
async def about(m): await m.answer(about_text(),reply_markup=about_keyboard())
@router.message(Command('stats'))
async def stats(m):
    if not is_admin(m.from_user.id): return
    async with SessionLocal() as s: users=(await s.scalar(select(func.count()).select_from(TelegramUser))); sales=(await s.scalar(select(func.count()).select_from(Order).where(Order.status=='paid')))
    await m.answer(f'Пользователей: {users}\nПродаж: {sales}')
@router.message(Command('orders'))
async def orders(m):
    if not is_admin(m.from_user.id): return
    async with SessionLocal() as s: rows=(await s.execute(select(Order).order_by(Order.created_at.desc()).limit(20))).scalars().all()
    await m.answer('\n'.join(f'{o.id} · {o.status} · {o.amount} {o.currency}' for o in rows) or 'Заказов нет')
@router.message(Command('payments'))
async def payments(m):
    if not is_admin(m.from_user.id): return
    async with SessionLocal() as s: rows=(await s.execute(select(Payment).order_by(Payment.created_at.desc()).limit(20))).scalars().all()
    await m.answer('\n'.join(f'{p.id} · {p.status} · {p.amount} {p.currency}' for p in rows) or 'Платежей нет')
@router.message(Command('plans'))
async def plans(m):
    if not is_admin(m.from_user.id): return
    rows=await active_plans(); await m.answer('\n'.join(f'{p.id} · {p.name} · {p.price} {p.currency}' for p in rows))
@router.message(Command('activation_log'))
async def activation_log(m):
    if not is_admin(m.from_user.id): return
    from database.models import ActivationAudit
    async with SessionLocal() as s: rows=(await s.execute(select(ActivationAudit).order_by(ActivationAudit.created_at.desc()).limit(20))).scalars().all()
    await m.answer('\n'.join(f'{a.created_at:%d.%m %H:%M} · {a.action} · {a.reason}' for a in rows) or 'Журнал пуст')
@router.message(Command('resend'))
async def resend(m,command:CommandObject):
    if not is_admin(m.from_user.id) or not command.args: return
    async with SessionLocal() as s: lic=await s.get(License,command.args.strip())
    if not lic or not lic.key_delivery_ciphertext: return await m.answer('Ключ не найден.')
    key=decrypt_delivery_secret(lic.key_delivery_ciphertext,cfg.server_pepper)
    await m.bot.send_message(lic.purchaser_telegram_id,f'Ваш лицензионный ключ:\n<code>{key}</code>')
    await m.answer('Ключ повторно отправлен владельцу.')
@router.message(Command('refund'))
async def refund(m,command:CommandObject):
    if not is_admin(m.from_user.id): return
    await m.answer('↩️ Возвраты Telegram Stars выполняются через <code>/admin</code> → «Лицензии» → карточка лицензии.')
@router.message(Command('backup'))
async def backup(m):
    if not is_admin(m.from_user.id): return
    path=await backup_database_async(); await m.answer_document(__import__('aiogram').types.FSInputFile(path))
@router.message(Command('license'))
async def find_license(m,command:CommandObject):
    if not is_admin(m.from_user.id) or not command.args: return
    tail=command.args[-4:].upper()
    async with SessionLocal() as s: rows=(await s.execute(select(License).where(License.key_last4==tail))).scalars().all()
    await m.answer('\n'.join(f'{l.id} {mask_key(l.key_last4)} {l.status}' for l in rows) or 'Не найдено')
@router.message(Command('block','unblock','revoke','reset_devices'))
async def dangerous(m,command:CommandObject):
    if not is_admin(m.from_user.id) or not command.args: return
    await m.answer('Подтвердите опасное действие:',reply_markup=confirm_keyboard(m.text.split()[0][1:],command.args))
@router.callback_query(F.data.startswith('admin_confirm:'))
async def confirm(c):
    if not is_admin(c.from_user.id): return await c.answer('Нет доступа',show_alert=True)
    _,action,target=c.data.split(':',2)
    async with SessionLocal() as s:
        lic=await s.get(License,target)
        if not lic: return await c.answer('Лицензия не найдена',show_alert=True)
        if action=='block': lic.status='blocked'
        elif action=='unblock': lic.status='active'
        elif action=='revoke': lic.status='revoked'
        elif action=='reset_devices':
            from database.models import LicenseDevice
            for d in (await s.execute(select(LicenseDevice).where(LicenseDevice.license_id==lic.id))).scalars(): d.active=False
        elif action=='refund':
            return await c.answer('Используйте /admin для подтверждённого возврата Stars',show_alert=True)
        else: return await c.answer('Неизвестное действие')
        s.add(AdminAction(admin_telegram_id=c.from_user.id,action=action,target_id=target)); await s.commit()
    await c.message.edit_text('Действие выполнено и записано в журнал.')
@router.callback_query(F.data=='admin_cancel')
async def cancel(c): await c.message.edit_text('Отменено.')
async def run_bot():
    if not cfg.bot_token: raise RuntimeError('BOT_TOKEN не задан')
    from aiogram.client.default import DefaultBotProperties
    from aiogram.types import BotCommand
    bot=Bot(cfg.bot_token,default=DefaultBotProperties(parse_mode='HTML'))
    await bot.set_my_commands([
        BotCommand(command='start',description='Запустить бота'),
        BotCommand(command='menu',description='Открыть главное меню'),
        BotCommand(command='paysupport',description='Поддержка по платежам'),
        BotCommand(command='phone',description='Сохранить номер для поддержки'),
    ])
    from aiogram.types import BotCommandScopeChat
    for admin_id in cfg.admin_id_set:
        await bot.set_my_commands([
            BotCommand(command='start',description='Запустить бота'),
            BotCommand(command='menu',description='Открыть главное меню'),
            BotCommand(command='paysupport',description='Поддержка по платежам'),
            BotCommand(command='admin',description='Открыть админ-панель'),
            BotCommand(command='setprice',description='Изменить цену тарифа'),
            BotCommand(command='plantoggle',description='Включить или выключить тариф'),
        ],scope=BotCommandScopeChat(chat_id=admin_id))
    dp=Dispatcher(); dp.include_router(admin_panel_router); dp.include_router(admin_license_router); dp.include_router(router); await dp.start_polling(bot)
def main(): asyncio.run(run_bot())
if __name__=='__main__': main()
