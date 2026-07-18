from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import select

from core.config import get_settings
from database.models import TelegramUser
from database.session import SessionLocal

public_commands_router = Router(name="public_commands")
cfg = get_settings()


def support_keyboard():
    rows = []
    if cfg.support_url:
        rows.append([InlineKeyboardButton(text="💬 Написать в поддержку", url=cfg.support_url)])
    rows.append([InlineKeyboardButton(text="💎 Выбрать тариф", callback_data="ui:plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@public_commands_router.message(Command("paysupport"))
async def payment_support(message):
    await message.answer(
        "<b>💳 ПОДДЕРЖКА ПО ОПЛАТЕ</b>\n\n"
        "Если Telegram Stars списались, но ключ не появился:\n"
        "1. Откройте раздел «Мои лицензии».\n"
        "2. Подождите 1–2 минуты и проверьте ещё раз.\n"
        "3. Если лицензии нет — напишите в поддержку.\n\n"
        "В сообщении укажите время платежа и выбранный тариф. "
        "Не отправляйте лицензионный ключ полностью.",
        reply_markup=support_keyboard(),
    )


@public_commands_router.message(Command("phone"))
async def phone_command(message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Нажмите кнопку отправки номера",
    )
    await message.answer(
        "<b>📱 НОМЕР ТЕЛЕФОНА</b>\n\n"
        "Нажмите кнопку ниже, чтобы привязать свой номер к профилю поддержки.\n"
        "Можно отменить действие.",
        reply_markup=keyboard,
    )


@public_commands_router.message(F.contact)
async def save_phone_contact(message):
    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        return await message.answer(
            "Отправьте именно свой номер через кнопку «📱 Отправить мой номер».",
            reply_markup=ReplyKeyboardRemove(),
        )
    phone = (contact.phone_number or "").strip()
    if not phone:
        return await message.answer("Номер телефона не получен.", reply_markup=ReplyKeyboardRemove())
    async with SessionLocal() as session:
        user = (await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == message.from_user.id)
        )).scalar_one_or_none()
        if not user:
            user = TelegramUser(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
            session.add(user)
            await session.flush()
        if hasattr(user, "phone"):
            user.phone = phone
        await session.commit()
    await message.answer(
        f"Номер <code>{escape(phone)}</code> сохранён.",
        reply_markup=ReplyKeyboardRemove(),
    )


@public_commands_router.message(F.text == "Отмена")
async def cancel_phone(message):
    await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())
