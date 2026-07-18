from __future__ import annotations

from html import escape
from typing import Iterable

BRAND = "◈  КРИПТО МИНЬОН"
STATUS_LABELS = {
    "pending": "🟡 Ожидает активации",
    "active": "🟢 Активна",
    "expired": "⚪ Истекла",
    "blocked": "🔴 Заблокирована",
    "revoked": "⛔ Отозвана",
    "refunded": "↩️ Возвращена",
}


def divider() -> str:
    return "━━━━━━━━━━━━━━━━━━━━"


def welcome_text(first_name: str | None = None) -> str:
    name = escape(first_name or "пользователь")
    return (
        f"<b>{BRAND}</b>\n"
        f"<code>ЛИЦЕНЗИОННЫЙ ЦЕНТР</code>\n\n"
        f"Привет, <b>{name}</b>! 👋\n"
        "Здесь можно выбрать тариф, получить лицензию и управлять доступом к приложению.\n\n"
        f"{divider()}\n"
        "✨ <b>Что внутри</b>\n"
        "• безопасная активация устройства\n"
        "• личный кабинет лицензий\n"
        ""
        "• быстрая поддержка\n"
        f"{divider()}\n\n"
        "<i>ℹ️ Подробная информация — в разделе «Условия использования».</i>\n\n"
        "<b>Выберите действие ниже</b> ↓"
    )


def plans_text() -> str:
    return (
        f"<b>{BRAND}</b>\n"
        "<code>ВЫБОР ТАРИФА</code>\n\n"
        "Выберите подходящий срок доступа. Перед оформлением вы увидите все параметры тарифа.\n\n"
        "🔐 Безопасная активация\n"
        "💻 Привязка к разрешённому числу устройств\n"
        "⚡ Ключ доступен сразу после подтверждения"
    )


def plan_card(plan) -> str:
    duration = "Без ограничения срока" if plan.duration_days is None else f"{plan.duration_days} дней"
    starts = "после оплаты" if plan.starts_on == "payment" else "после первой активации"
    features = []
    try:
        import json
        raw = json.loads(plan.features or "[]")
        names = {
            "scanner_simulation": "Seed-сканер",
            "virtual_balance": "Поддержка",
            "personal_account": "Личный кабинет",
        }
        features = [names.get(item, str(item).replace("_", " ").title()) for item in raw]
    except (TypeError, ValueError):
        features = []
    feature_text = "\n".join(f"  ✓ {escape(item)}" for item in features) or "  ✓ Основные функции приложения"
    return (
        f"<b>{BRAND}</b>\n"
        "<code>КАРТОЧКА ТАРИФА</code>\n\n"
        f"💎 <b>{escape(plan.name)}</b>\n"
        f"{escape(plan.description)}\n\n"
        f"{divider()}\n"
        f"⭐ <b>Стоимость:</b> {plan.price} {escape(plan.currency)}\n"
        f"⏳ <b>Срок:</b> {duration}\n"
        f"🚀 <b>Начало:</b> {starts}\n"
        f"💻 <b>Устройств:</b> {plan.max_devices}\n"
        f"{divider()}\n\n"
        f"<b>Доступные возможности</b>\n{feature_text}"
    )


def licenses_text(rows: Iterable[tuple]) -> str:
    rows = list(rows)
    if not rows:
        return (
            f"<b>{BRAND}</b>\n<code>МОИ ЛИЦЕНЗИИ</code>\n\n"
            "📭 <b>Здесь пока пусто</b>\n"
            "После покупки ваша лицензия появится в этом разделе."
        )
    cards = []
    for license_obj, plan, shown_key in rows:
        if license_obj.expires_at:
            expires = f"до {license_obj.expires_at.strftime('%d.%m.%Y')}"
        elif plan.duration_days is None:
            expires = "бессрочно"
        elif plan.starts_on == "activation":
            expires = f"{plan.duration_days} дней с момента активации"
        else:
            expires = f"{plan.duration_days} дней с момента оплаты"
        created = license_obj.created_at.strftime("%d.%m.%Y · %H:%M")
        cards.append(
            f"<b>💎 {escape(plan.name)}</b>\n"
            f"{STATUS_LABELS.get(license_obj.status, escape(license_obj.status))}\n"
            f"🔑 <code>{escape(shown_key)}</code>\n"
            f"💻 Устройств: {license_obj.activation_count}/{license_obj.max_devices}\n"
            f"📅 Срок: {expires}\n"
            f"🕘 Получена: {created}"
        )
    return (
        f"<b>{BRAND}</b>\n<code>МОИ ЛИЦЕНЗИИ</code>\n"
        "<i>Сначала показаны новые лицензии</i>\n\n"
        + f"\n\n{divider()}\n\n".join(cards)
    )
def guide_text() -> str:
    return (
        f"<b>{BRAND}</b>\n<code>БЫСТРЫЙ СТАРТ</code>\n\n"
        "🚀 <b>От ключа до запуска — меньше минуты</b>\n"
        "Пройдите четыре коротких шага, и приложение будет готово к работе.\n\n"
        "<b>01  📥 Загрузите приложение</b>\n"
        "Используйте официальную версию из раздела «Скачать».\n\n"
        "<b>02  🔑 Возьмите свой ключ</b>\n"
        "Он всегда доступен в разделе «Мои лицензии».\n\n"
        "<b>03  ⚡ Активируйте доступ</b>\n"
        "Вставьте ключ в стартовое окно приложения и нажмите «Активировать».\n\n"
        "<b>04  ✨ Всё готово</b>\n"
        "После подтверждения откроется главное окно «Крипто Миньон».\n\n"
        "<blockquote>💡 При следующем запуске лицензия проверится автоматически — повторно вводить ключ не потребуется.</blockquote>"
    )

def about_text() -> str:
    return '<b>◈  КРИПТО МИНЬОН</b>\n<code>О ПРОЕКТЕ</code>\n\n✨ <b>Познакомьтесь с «Крипто Миньон» ближе</b>\nМы собрали полный обзор проекта в одной удобной статье.\n\n<b>01  🎮 Узнайте о приложении</b>\nПосмотрите, как устроен проект и какие возможности доступны внутри.\n\n<b>02  🧩 Изучите функции</b>\nИнтерфейс, сценарии использования и ключевые особенности — без лишней воды.\n\n<b>03  🛡 Разберитесь в лицензировании</b>\nВ обзоре описана система доступа и взаимодействие с приложением.\n\n<b>04  📖 Откройте полный обзор</b>\nНажмите кнопку ниже — статья откроется в Telegraph.'
def terms_text() -> str:
    return (
        f"<b>{BRAND}</b>\n<code>УСЛОВИЯ ИСПОЛЬЗОВАНИЯ</code>\n\n"
        "Актуальная редакция условий опубликована в Telegraph."
    )

