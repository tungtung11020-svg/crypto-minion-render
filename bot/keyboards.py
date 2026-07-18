from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

TERMS_URL = "https://telegra.ph/Kripto-Minon-Obzor-ehkosistemy-i-polzovatelskogo-opyta-07-18"
ABOUT_URL = "https://telegra.ph/Kripto-Minon-30-Obzor-programmnogo-resheniya-07-18"


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Выбрать тариф", callback_data="ui:plans")],
        [InlineKeyboardButton(text="🔑 Мои лицензии", callback_data="ui:licenses")],
        [
            InlineKeyboardButton(text="📖 Активация", callback_data="ui:guide"),
            InlineKeyboardButton(text="📥 Скачать", callback_data="ui:download"),
        ],
        [
            InlineKeyboardButton(text="💬 Поддержка", callback_data="ui:support"),
            InlineKeyboardButton(text="✨ О проекте", callback_data="ui:about"),
        ],
        [InlineKeyboardButton(text="📜 Условия использования", url=TERMS_URL)],
    ])


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 Купить ключ"), KeyboardButton(text="🔑 Мои лицензии")],
            [KeyboardButton(text="📖 Как активировать"), KeyboardButton(text="📥 Скачать приложение")],
            [KeyboardButton(text="💬 Поддержка"), KeyboardButton(text="✨ О программе")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел…",
    )


def plans_keyboard(plans) -> InlineKeyboardMarkup:
    buttons = []
    for plan in plans:
        icon = "♾" if plan.duration_days is None else "💎"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {plan.name}  ·  {plan.price} ⭐",
            callback_data=f"plan:{plan.id}",
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад в меню", callback_data="ui:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def plan_actions(plan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Оформить лицензию", callback_data=f"buy:{plan_id}")],
        [InlineKeyboardButton(text="‹ К тарифам", callback_data="ui:plans")],
    ])


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="‹ Главное меню", callback_data="ui:home")],
    ])


def about_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Читать обзор в Telegraph", url=ABOUT_URL)],
        [InlineKeyboardButton(text="‹ Главное меню", callback_data="ui:home")],
    ])


def licenses_keyboard(has_licenses: bool, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    rows = []
    if not has_licenses:
        rows.append([InlineKeyboardButton(text="💎 Выбрать тариф", callback_data="ui:plans")])
    if total_pages > 1:
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(text="‹ Назад", callback_data=f"ui:licenses:{page-1}"))
        if page + 1 < total_pages:
            navigation.append(InlineKeyboardButton(text="Вперёд ›", callback_data=f"ui:licenses:{page+1}"))
        if navigation:
            rows.append(navigation)
    rows.append([InlineKeyboardButton(text="↻ Обновить страницу", callback_data=f"ui:licenses:{page}")])
    rows.append([InlineKeyboardButton(text="‹ Главное меню", callback_data="ui:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
def download_keyboard(url: str) -> InlineKeyboardMarkup:
    rows = []
    if url and url.startswith(("https://", "http://")):
        rows.append([InlineKeyboardButton(text="📥 Скачать «Крипто Миньон»", url=url)])
    rows.append([InlineKeyboardButton(text="📖 Инструкция по активации", callback_data="ui:guide")])
    rows.append([InlineKeyboardButton(text="‹ Главное меню", callback_data="ui:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_keyboard(url: str) -> InlineKeyboardMarkup:
    rows = []
    if url and url.startswith(("https://", "http://")):
        rows.append([InlineKeyboardButton(text="💬 Открыть поддержку", url=url)])
    rows.append([InlineKeyboardButton(text="‹ Главное меню", callback_data="ui:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(action, target):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✓ Подтвердить", callback_data=f"admin_confirm:{action}:{target}"),
        InlineKeyboardButton(text="Отмена", callback_data="admin_cancel"),
    ]])
