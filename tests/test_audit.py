from tests.conftest import login


def test_login_writes_audit_log(client, admin_user):
    login(client)
    from app.audit.models import AuditLog

    entry = AuditLog.query.filter_by(action="auth.login").first()
    assert entry is not None
    assert entry.result == "success"


def test_failed_login_writes_audit_log(client, admin_user):
    login(client, pin="0007")
    from app.audit.models import AuditLog

    entry = AuditLog.query.filter_by(action="auth.login_failed").first()
    assert entry is not None
    assert entry.result == "failure"


def test_role_switch_writes_audit_log(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    from app.audit.models import AuditLog

    entry = AuditLog.query.filter_by(action="role.switch").first()
    assert entry is not None
