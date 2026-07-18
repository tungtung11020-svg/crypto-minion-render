from bot.admin_license_controls import allowed_actions

def test_controls_by_status():
    assert 'block' in allowed_actions('active') and 'unblock' not in allowed_actions('active')
    assert 'unblock' in allowed_actions('blocked') and 'block' not in allowed_actions('blocked')
    assert allowed_actions('revoked')==['info']

def test_callback_contract_present():
    import inspect,bot.admin_license_controls as m
    src=inspect.getsource(m)
    for value in ['alc:confirm:reset','alc:reason:block','alc:confirm:unblock','alc:reason:revoke','show_alert=True','ActivationAudit','AdminAction']:
        assert value in src

def test_bearer_validate_contract_present():
    from pathlib import Path
    api=Path('api/main.py').read_text(encoding='utf-8'); service=Path('services/activation.py').read_text(encoding='utf-8')
    assert "authorization.startswith('Bearer ')" in api
    for code in ['LICENSE_BLOCKED','LICENSE_REVOKED','LICENSE_EXPIRED','DEVICE_RESET','LICENSE_VALID']:
        assert code in service or code in api
