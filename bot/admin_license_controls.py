from datetime import timezone
from html import escape
import json

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select

from core.config import get_settings
from core.license_keys import mask_key
from core.security import sha256_text
from database.models import ActivationAudit, AdminAction, License, LicenseDevice, Plan, utcnow
from database.session import SessionLocal

admin_license_router = Router(name="admin_license_controls")
cfg = get_settings()


class LicenseReasonStates(StatesGroup):
    waiting_reason = State()
    confirming_reason = State()


def is_admin(uid: int) -> bool:
    return uid in cfg.admin_id_set


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def allowed_actions(status: str):
    actions = ["info"]
    if status not in {"revoked", "refunded"}:
        actions.append("reset")
    if status == "blocked":
        actions.append("unblock")
    elif status not in {"revoked", "refunded", "expired"}:
        actions.append("block")
    if status not in {"revoked", "refunded"}:
        actions.append("revoke")
    return actions


def controls(license_row):
    actions = allowed_actions(license_row.status)
    rows = [[InlineKeyboardButton(text="ℹ️ Информация", callback_data=f"alc:info:{license_row.id}")]]
    if "reset" in actions:
        rows.append([InlineKeyboardButton(text="♻️ Сбросить устройства", callback_data=f"alc:confirm:reset:{license_row.id}")])
    if "block" in actions:
        rows.append([InlineKeyboardButton(text="🔴 Заблокировать", callback_data=f"alc:reason:block:{license_row.id}")])
    if "unblock" in actions:
        rows.append([InlineKeyboardButton(text="🟢 Разблокировать", callback_data=f"alc:confirm:unblock:{license_row.id}")])
    if "revoke" in actions:
        rows.append([InlineKeyboardButton(text="⛔ Отозвать", callback_data=f"alc:reason:revoke:{license_row.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(action: str, license_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✓ Подтвердить", callback_data=f"alc:do:{action}:{license_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"alc:cancel:{license_id}")],
    ])


def reason_cancel_keyboard(license_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data=f"alc:reason_cancel:{license_id}")]
    ])


def reason_confirm_keyboard(action: str, license_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✓ Подтвердить", callback_data=f"alc:reason_do:{action}:{license_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"alc:reason_cancel:{license_id}")],
    ])


async def card(license_id: str):
    async with SessionLocal() as session:
        row = (await session.execute(
            select(License, Plan)
            .join(Plan, License.plan_id == Plan.id)
            .where(License.id == license_id)
        )).first()
        if not row:
            return "Лицензия не найдена", None
        license_row, plan = row
        active = await session.scalar(
            select(func.count()).select_from(LicenseDevice).where(
                LicenseDevice.license_id == license_id,
                LicenseDevice.active == True,
            )
        ) or 0
    expiration = license_row.expires_at.strftime("%d.%m.%Y") if license_row.expires_at else "бессрочно"
    reason = escape((license_row.status_reason or "").strip())
    reason_line = f"\nПричина: <b>{reason}</b>" if reason else ""
    text = (
        f"<b>🔑 КАРТОЧКА ЛИЦЕНЗИИ</b>\n\n"
        f"UUID лицензии: <code>{license_row.id}</code>\n"
        f"Ключ: <code>{mask_key(license_row.key_last4)}</code>\n"
        f"Последние 4 символа: <code>{license_row.key_last4}</code>\n"
        f"Тариф: <b>{escape(plan.name)}</b>\n"
        f"Статус: <b>{escape(license_row.status)}</b>{reason_line}\n"
        f"Пользователь: <code>{license_row.purchaser_telegram_id}</code>\n"
        f"Устройства: <b>{active}/{license_row.max_devices}</b>\n"
        f"Действует до: <b>{expiration}</b>"
    )
    return text, controls(license_row)


async def write_audit(session, admin_id: int, license_id: str, action: str, reason: str, changed: bool):
    details = json.dumps({"reason": reason, "changed": changed}, ensure_ascii=False)
    session.add(AdminAction(
        admin_telegram_id=admin_id,
        action=action,
        target_id=license_id,
        details=details,
    ))
    session.add(ActivationAudit(
        identifier_hash=sha256_text(f"admin:{admin_id}"),
        license_id=license_id,
        action=f"admin_{action}",
        success=True,
        reason=reason or ("changed" if changed else "idempotent_noop"),
    ))


async def apply_action(admin_id: int, license_id: str, action: str, reason: str = ""):
    now = utcnow()
    async with SessionLocal() as session:
        async with session.begin():
            license_row = await session.get(License, license_id)
            if not license_row:
                return "Лицензия не найдена", False

            changed = False
            if action == "reset":
                devices = (await session.execute(
                    select(LicenseDevice).where(LicenseDevice.license_id == license_id)
                )).scalars().all()
                changed = any(device.active for device in devices) or license_row.activation_count != 0
                for device in devices:
                    device.active = False
                license_row.activation_count = 0
                message = "Устройства лицензии сброшены" if changed else "Устройства лицензии уже сброшены"
            elif action == "block":
                reason = reason.strip()
                if len(reason) < 3 or len(reason) > 500:
                    return "Причина должна содержать от 3 до 500 символов", False
                changed = license_row.status != "blocked" or license_row.status_reason != reason
                license_row.status = "blocked"
                license_row.status_reason = reason
                license_row.status_changed_at = now
                license_row.status_changed_by = admin_id
                message = "Ключ заблокирован"
            elif action == "unblock":
                changed = license_row.status == "blocked"
                if changed:
                    expiration = aware(license_row.expires_at)
                    license_row.status = "expired" if expiration and expiration <= now else ("active" if license_row.activated_at else "pending")
                license_row.status_reason = None
                license_row.status_changed_at = now
                license_row.status_changed_by = admin_id
                message = "Ключ разблокирован" if changed else "Ключ уже разблокирован"
            elif action == "revoke":
                reason = reason.strip()
                if len(reason) < 3 or len(reason) > 500:
                    return "Причина должна содержать от 3 до 500 символов", False
                changed = license_row.status != "revoked" or license_row.status_reason != reason
                license_row.status = "revoked"
                license_row.status_reason = reason
                license_row.status_changed_at = now
                license_row.status_changed_by = admin_id
                message = "Лицензия отозвана"
            else:
                return "Неизвестное действие", False

            await write_audit(session, admin_id, license_id, action, reason, changed)
    return message, True


@admin_license_router.message(Command("license"))
async def license_find(message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    query = (command.args or "").strip()
    if not query:
        return await message.answer("Введите UUID или последние 4 символа: <code>/license A1B2</code>")
    async with SessionLocal() as session:
        license_row = await session.get(License, query)
        if not license_row:
            rows = (await session.execute(
                select(License)
                .where(License.key_last4 == query[-4:].upper())
                .order_by(License.created_at.desc())
            )).scalars().all()
            if len(rows) > 1:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"{mask_key(item.key_last4)} · {item.status}",
                        callback_data=f"alc:info:{item.id}",
                    )] for item in rows[:10]
                ])
                return await message.answer("Найдено несколько лицензий. Выберите нужную:", reply_markup=keyboard)
            license_row = rows[0] if rows else None
    if not license_row:
        return await message.answer("Лицензия не найдена")
    text, keyboard = await card(license_row.id)
    await message.answer(text, reply_markup=keyboard)


@admin_license_router.callback_query(F.data.startswith("alc:reason:"))
async def request_reason(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    _, _, action, license_id = callback.data.split(":", 3)
    if action not in {"block", "revoke"}:
        return await callback.answer("Некорректное действие", show_alert=True)
    async with SessionLocal() as session:
        license_row = await session.get(License, license_id)
    if not license_row or action not in allowed_actions(license_row.status):
        return await callback.answer("Действие недоступно", show_alert=True)
    await state.clear()
    await state.set_state(LicenseReasonStates.waiting_reason)
    await state.update_data(action=action, license_id=license_id)
    prompt = "Укажите причину блокировки" if action == "block" else "Укажите причину отзыва"
    await callback.message.edit_text(
        f"<b>{prompt}</b>\n\nОт 3 до 500 символов.",
        reply_markup=reason_cancel_keyboard(license_id),
    )
    await callback.answer()


@admin_license_router.message(LicenseReasonStates.waiting_reason)
async def receive_reason(message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    reason = (message.text or "").strip()
    if len(reason) < 3:
        return await message.answer("Причина слишком короткая. Введите минимум 3 символа.")
    if len(reason) > 500:
        return await message.answer("Причина слишком длинная. Максимум 500 символов.")
    data = await state.get_data()
    action = data.get("action")
    license_id = data.get("license_id")
    if action not in {"block", "revoke"} or not license_id:
        await state.clear()
        return await message.answer("Сессия действия устарела. Откройте карточку лицензии заново.")
    await state.update_data(reason=reason)
    await state.set_state(LicenseReasonStates.confirming_reason)
    action_name = "Блокировка" if action == "block" else "Отзыв лицензии"
    await message.answer(
        f"<b>⚠️ Подтверждение</b>\n\n"
        f"Действие: <b>{action_name}</b>\n"
        f"Лицензия: <code>{license_id}</code>\n"
        f"Причина: <b>{escape(reason)}</b>",
        reply_markup=reason_confirm_keyboard(action, license_id),
    )


@admin_license_router.callback_query(F.data.startswith("alc:reason_do:"))
async def confirm_reason_action(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    _, _, action, license_id = callback.data.split(":", 3)
    data = await state.get_data()
    if data.get("action") != action or data.get("license_id") != license_id:
        await state.clear()
        return await callback.answer("Подтверждение устарело", show_alert=True)
    reason = (data.get("reason") or "").strip()
    if len(reason) < 3 or len(reason) > 500:
        await state.clear()
        return await callback.answer("Причина недействительна", show_alert=True)
    result, ok = await apply_action(callback.from_user.id, license_id, action, reason)
    await state.clear()
    text, keyboard = await card(license_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(result, show_alert=True)


@admin_license_router.callback_query(F.data.startswith("alc:reason_cancel:"))
async def cancel_reason(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    license_id = callback.data.split(":", 2)[2]
    await state.clear()
    text, keyboard = await card(license_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("Действие отменено", show_alert=True)


@admin_license_router.callback_query(F.data.startswith("alc:"))
async def license_callback(callback, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)
    parts = callback.data.split(":")
    mode = parts[1]
    if mode in {"info", "cancel"} and len(parts) == 3:
        await state.clear()
        text, keyboard = await card(parts[2])
        await callback.message.edit_text(text, reply_markup=keyboard)
        return await callback.answer()
    if mode == "confirm" and len(parts) == 4:
        action, license_id = parts[2], parts[3]
        if action in {"block", "revoke"}:
            return await callback.answer("Для действия необходимо указать причину", show_alert=True)
        async with SessionLocal() as session:
            license_row = await session.get(License, license_id)
        if not license_row or action not in allowed_actions(license_row.status):
            return await callback.answer("Действие недоступно", show_alert=True)
        await callback.message.edit_text(
            "<b>⚠️ Подтверждение</b>\n\nПроверьте выбранную лицензию.",
            reply_markup=confirm_keyboard(action, license_id),
        )
        return await callback.answer()
    if mode != "do" or len(parts) != 4:
        return await callback.answer("Некорректная команда", show_alert=True)
    action, license_id = parts[2], parts[3]
    if action in {"block", "revoke"}:
        return await callback.answer("Для действия необходимо указать причину", show_alert=True)
    result, ok = await apply_action(callback.from_user.id, license_id, action)
    text, keyboard = await card(license_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(result, show_alert=True)
