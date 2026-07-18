from pathlib import Path
import inspect


def test_admin_panel_buttons_contract():
    import bot.admin_panel as module
    source = inspect.getsource(module)
    for value in [
        "ap:stats", "ap:license_search", "ap:orders", "ap:payments",
        "ap:plans", "ap:activation_log", "ap:backup", "ap:set_price:",
        "waiting_plan_price", "set_plan_price", "toggle_plan",
    ]:
        assert value in source


def test_admin_panel_router_connected():
    source = Path("bot/main.py").read_text(encoding="utf-8")
    assert "from bot.admin_panel import admin_panel_router" in source
    assert "dp.include_router(admin_panel_router)" in source
