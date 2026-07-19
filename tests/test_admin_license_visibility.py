from pathlib import Path


def test_license_identifiers_are_visible():
    controls = Path("bot/admin_license_controls.py").read_text(encoding="utf-8")
    panel = Path("bot/admin_panel.py").read_text(encoding="utf-8")
    assert "UUID лицензии:" in controls
    assert "Последние 4 символа:" in controls
    assert 'callback_data=f"alc:info:{item.id}"' in panel
    assert "ap:license_query" in panel
    assert "License.order_id == Order.id" in panel
    assert "UUID: <code>{row.license_id}</code>" in panel
