from html import escape
import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select

from bot.admin_license_controls import card as license_card
from core.config import get_settings
from core.license_keys import mask_key
from database.backup import backup_database_async
from database.models import ActivationAudit, AdminAction, License, Order, Payment, Plan, TelegramUser
from database.session import SessionLocal

admin_panel_router = Router(name="admin_panel_buttons")
cfg = get_settings()


class AdminPanelStates(StatesGroup):
    waiting_license_query = State()
    waiting_plan_price = State()


def is_admin(user_id: int) -> bool:
    return user_id in cfg.admin_id_set


def panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="ap:stats"),
            InlineKeyboardButton(text="🔑 Лицензии", callback_data="ap:license_search"),
        ],
        [
            InlineKeyboardButton(text="🧾 Заказы", callback_data="ap:orders"),
            InlineKeyboardButton(text="💳 Платежи", callback_data="ap:payments"),
        ],
        [
            InlineKeyboardButton(text="💰 Тарифы и цены", callback_data="ap:plans"),
            InlineKeyboardButton(text="📋 Активации", callback_data="ap:activation_log"),
        ],
        [InlineKeyboardButton(text="💾 Создать backup", callback_data="ap:backup")],
        [InlineKeyboardButton(text="🔄 Обновить панель", callback_data="ap:home")],
    ])


def back_keyboard(destination: str = "home"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=f"ap:{destination}")]
    ])


def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="ap:cancel")]
    ])


def plan_keyboard(plan: Plan):
    toggle_text = "⏸ Выключить тариф" if plan.is_active else "▶️ Включить тариф"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"ap:set_price:{plan.id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"ap:toggle_plan:{plan.id}")],
        [InlineKeyboardButton(text="← К тарифам", callback_data="ap:plans")],
    ])


async def panel_text():
    async with SessionLocal() as session:
        users = await session.scalar(select(func.count()).select_from(TelegramUser)) or 0
        licenses = await session.scalar(select(func.count()).select_from(License)) or 0
        active = await session.scalar(select(func.count()).select_from(License).where(License.status == "active")) or 0
        paid = await session.scalar(select(func.count()).select_from(Order).where(Order.status == "paid")) or 0
    return (
        "<b>⚙️ АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Пользователей: <b>{users}</b>\n"
        f"Лицензий: <b>{licenses}</b>\n"
        f"Активных: <b>{active}</b>\n"
        f"Оплаченных заказов: <b>{paid}</b>\n\n"
        "Выберите раздел:"
    )


async def show_home(target, edit: bool = True):
    text = await panel_text()
    if edit:
        await target.edit_text(text, reply_markup=panel_keyboard())
    else:
        await target.answer(text, reply_markup=panel_keyboard())


async def plans_text_and_keyboard():
    async with SessionLocal() as session:
        plans = (await session.execute(select(Plan).order_by(Plan.price, Plan.name))).scalars().all()
    if not plans:
        return "<b>💰 Тарифы</b>\n\nТарифов пока нет.", back_keyboard()
    rows = []
    for plan in plans:
        status = "🟢" if plan.is_active else "⚫"
        rows.append([InlineKeyboardButton(
            text=f"{status} {plan.name} — {plan.price} {plan.currency}",
            callback_data=f"ap:plan:{plan.id}",
        )])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="ap:home")])
    return "<b>💰 ТАРИФЫ И ЦЕНЫ</b>\n\nНажмите тариф для управления:", InlineKeyboardMarkup(inline_keyboard=rows)


async def show_plan(callback, plan_id: str):
    async with SessionLocal() as session:
        plan = await session.get(Plan, plan_id)
    if not plan:
        return await callback.answer("Тариф не найден", show_alert=True)
    duration = "бессрочно" if plan.duration_days is None else f"{plan.duration_days} дней"
    status = "включён" if plan.is_active else "выключен"
    text = (
        f"<b>💰 {escape(plan.name)}</b>\n\n"
        f"Цена: <b>{plan.price} {escape(plan.currency)}</b>\n"
        f"Срок: <b>{duration}</b>\n"
        f"Устройств: <b>{plan.max_devices}</b>\n"
        f"Статус: <b>{status}</b>"
    )
    await callback.message.edit_text(text, reply_markup=plan_keyboard(plan))


@admin_panel_router.message(Command("admin"))
async def admin_command(message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await show_home(message, edit=False)


@admin_panel_router.callback_query(F.data == "ap:home")
async def home_callback(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    await state.clear()
    await show_home(callback.message)
    await callback.answer()


@admin_panel_router.callback_query(F.data == "ap:stats")
async def stats_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    async with SessionLocal() as session:
        users = await session.scalar(select(func.count()).select_from(TelegramUser)) or 0
        licenses = await session.scalar(select(func.count()).select_from(License)) or 0
        active = await session.scalar(select(func.count()).select_from(License).where(License.status == "active")) or 0
        blocked = await session.scalar(select(func.count()).select_from(License).where(License.status == "blocked")) or 0
        revoked = await session.scalar(select(func.count()).select_from(License).where(License.status == "revoked")) or 0
        orders = await session.scalar(select(func.count()).select_from(Order)) or 0
        paid = await session.scalar(select(func.count()).select_from(Order).where(Order.status == "paid")) or 0
        stars = await session.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "paid")) or 0
    text = (
        "<b>📊 СТАТИСТИКА</b>\n\n"
        f"Пользователей: <b>{users}</b>\n"
        f"Лицензий: <b>{licenses}</b>\n"
        f"Активных: <b>{active}</b>\n"
        f"Заблокированных: <b>{blocked}</b>\n"
        f"Отозванных: <b>{revoked}</b>\n"
        f"Заказов: <b>{orders}</b>\n"
        f"Оплачено: <b>{paid}</b>\n"
        f"Получено: <b>{stars} ⭐</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@admin_panel_router.callback_query(F.data == "ap:license_search")
async def license_search_callback(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminPanelStates.waiting_license_query)
    await callback.message.edit_text(
        "<b>🔑 ПОИСК ЛИЦЕНЗИИ</b>\n\nОтправьте UUID лицензии или последние 4 символа ключа.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@admin_panel_router.message(AdminPanelStates.waiting_license_query)
async def receive_license_query(message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    query = (message.text or "").strip()
    if not query:
        return await message.answer("Введите UUID или последние 4 символа ключа.")
    async with SessionLocal() as session:
        license_row = await session.get(License, query)
        if not license_row:
            rows = (await session.execute(
                select(License)
                .where(License.key_last4 == query[-4:].upper())
                .order_by(License.created_at.desc())
            )).scalars().all()
        else:
            rows = [license_row]
    if not rows:
        return await message.answer("Лицензия не найдена. Попробуйте ещё раз.", reply_markup=cancel_keyboard())
    await state.clear()
    if len(rows) == 1:
        text, keyboard = await license_card(rows[0].id)
        return await message.answer(text, reply_markup=keyboard)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{mask_key(item.key_last4)} · {item.status}",
            callback_data=f"alc:info:{item.id}",
        )] for item in rows[:10]
    ] + [[InlineKeyboardButton(text="← В админ-панель", callback_data="ap:home")]])
    await message.answer("Найдено несколько лицензий:", reply_markup=keyboard)


@admin_panel_router.callback_query(F.data == "ap:plans")
async def plans_callback(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    await state.clear()
    text, keyboard = await plans_text_and_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@admin_panel_router.callback_query(F.data.startswith("ap:plan:"))
async def plan_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    await show_plan(callback, callback.data.split(":", 2)[2])
    await callback.answer()


@admin_panel_router.callback_query(F.data.startswith("ap:set_price:"))
async def set_price_callback(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    plan_id = callback.data.split(":", 2)[2]
    async with SessionLocal() as session:
        plan = await session.get(Plan, plan_id)
    if not plan:
        return await callback.answer("Тариф не найден", show_alert=True)
    await state.set_state(AdminPanelStates.waiting_plan_price)
    await state.update_data(plan_id=plan_id)
    await callback.message.edit_text(
        f"<b>Новая цена тарифа «{escape(plan.name)}»</b>\n\n"
        f"Текущая цена: <b>{plan.price} {escape(plan.currency)}</b>\n"
        "Отправьте новую цену целым числом от 1 до 1 000 000.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@admin_panel_router.message(AdminPanelStates.waiting_plan_price)
async def receive_plan_price(message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        return await message.answer("Цена должна быть целым числом, например: <code>299</code>")
    price = int(raw)
    if price < 1 or price > 1_000_000:
        return await message.answer("Допустимая цена: от 1 до 1 000 000.")
    data = await state.get_data()
    plan_id = data.get("plan_id")
    async with SessionLocal() as session:
        async with session.begin():
            plan = await session.get(Plan, plan_id)
            if not plan:
                await state.clear()
                return await message.answer("Тариф не найден.")
            old_price = plan.price
            plan.price = price
            session.add(AdminAction(
                admin_telegram_id=message.from_user.id,
                action="set_plan_price",
                target_id=plan.id,
                details=json.dumps({"old_price": old_price, "new_price": price, "currency": plan.currency}, ensure_ascii=False),
            ))
            plan_name = plan.name
            currency = plan.currency
    await state.clear()
    await message.answer(
        f"Цена тарифа <b>{escape(plan_name)}</b> изменена: "
        f"<s>{old_price}</s> → <b>{price} {escape(currency)}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← К тарифам", callback_data="ap:plans")],
            [InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="ap:home")],
        ]),
    )


@admin_panel_router.callback_query(F.data.startswith("ap:toggle_plan:"))
async def toggle_plan_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    plan_id = callback.data.split(":", 2)[2]
    async with SessionLocal() as session:
        async with session.begin():
            plan = await session.get(Plan, plan_id)
            if not plan:
                return await callback.answer("Тариф не найден", show_alert=True)
            plan.is_active = not plan.is_active
            session.add(AdminAction(
                admin_telegram_id=callback.from_user.id,
                action="toggle_plan",
                target_id=plan.id,
                details=json.dumps({"is_active": plan.is_active}, ensure_ascii=False),
            ))
            enabled = plan.is_active
    await show_plan(callback, plan_id)
    await callback.answer("Тариф включён" if enabled else "Тариф выключен", show_alert=True)


@admin_panel_router.callback_query(F.data == "ap:orders")
async def orders_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    async with SessionLocal() as session:
        rows = (await session.execute(select(Order).order_by(Order.created_at.desc()).limit(15))).scalars().all()
    lines = ["<b>🧾 ПОСЛЕДНИЕ ЗАКАЗЫ</b>"]
    for row in rows:
        lines.append(f"<code>{row.id[:8]}</code> · {row.amount} {escape(row.currency)} · <b>{escape(row.status)}</b>")
    if not rows:
        lines.append("\nЗаказов пока нет.")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_keyboard())
    await callback.answer()


@admin_panel_router.callback_query(F.data == "ap:payments")
async def payments_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    async with SessionLocal() as session:
        rows = (await session.execute(select(Payment).order_by(Payment.created_at.desc()).limit(15))).scalars().all()
    lines = ["<b>💳 ПОСЛЕДНИЕ ПЛАТЕЖИ</b>"]
    for row in rows:
        lines.append(f"<code>{row.id[:8]}</code> · {row.amount} {escape(row.currency)} · <b>{escape(row.status)}</b>")
    if not rows:
        lines.append("\nПлатежей пока нет.")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_keyboard())
    await callback.answer()


@admin_panel_router.callback_query(F.data == "ap:activation_log")
async def activation_log_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    async with SessionLocal() as session:
        rows = (await session.execute(
            select(ActivationAudit).order_by(ActivationAudit.created_at.desc()).limit(15)
        )).scalars().all()
    lines = ["<b>📋 ЖУРНАЛ АКТИВАЦИЙ</b>"]
    for row in rows:
        mark = "✅" if row.success else "❌"
        target = (row.license_id or "—")[:8]
        lines.append(f"{mark} <code>{target}</code> · {escape(row.action)} · {escape(row.reason[:80])}")
    if not rows:
        lines.append("\nЗаписей пока нет.")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_keyboard())
    await callback.answer()


@admin_panel_router.callback_query(F.data == "ap:backup")
async def backup_callback(callback):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    await callback.answer("Создаю резервную копию…")
    path = await backup_database_async()
    await callback.message.answer_document(
        FSInputFile(path),
        caption="Резервная копия SQLite создана.",
    )


@admin_panel_router.callback_query(F.data == "ap:cancel")
async def cancel_callback(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    await state.clear()
    await show_home(callback.message)
    await callback.answer("Отменено", show_alert=True)
