from pathlib import Path
import inspect


def test_reason_fsm_contract():
    import bot.admin_license_controls as module
    source = inspect.getsource(module)
    for value in [
        "LicenseReasonStates", "waiting_reason", "confirming_reason",
        "Укажите причину блокировки", "Укажите причину отзыва",
        "len(reason) < 3", "len(reason) > 500", "status_reason",
        "reason_do", "reason_cancel",
    ]:
        assert value in source


def test_live_validate_contract():
    service = Path("services/activation.py").read_text(encoding="utf-8")
    api = Path("api/main.py").read_text(encoding="utf-8")
    for code in ["LICENSE_BLOCKED", "LICENSE_REVOKED", "DEVICE_RESET", "LICENSE_EXPIRED", "REFUNDED"]:
        assert code in service or code in api
    assert "force_logout" in api
    assert "status_reason" in service


def test_model_reason_fields():
    model = Path("database/models.py").read_text(encoding="utf-8")
    for field in ["status_reason", "status_changed_at", "status_changed_by"]:
        assert field in model
