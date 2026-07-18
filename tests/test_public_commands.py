from pathlib import Path
import inspect


def test_phone_and_payment_support_handlers():
    import bot.public_commands as module
    source = inspect.getsource(module)
    for value in [
        'Command("paysupport")', 'Command("phone")',
        'request_contact=True', 'F.contact', 'ReplyKeyboardRemove',
        'support_url', 'TelegramUser',
    ]:
        assert value in source


def test_public_router_connected():
    source = Path("bot/main.py").read_text(encoding="utf-8")
    assert "from bot.public_commands import public_commands_router" in source
    assert "dp.include_router(public_commands_router)" in source
