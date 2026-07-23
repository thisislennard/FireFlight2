def test_init_fireflight_is_idempotent(app):
    runner = app.test_cli_runner()
    env = {"FIREFLIGHT_ADMIN_PIN": "4726"}

    result1 = runner.invoke(args=["init-fireflight"], env=env)
    assert result1.exit_code == 0, result1.output

    from app.auth.models import User
    from app.organizations.models import Organization
    from app.roles.models import Role

    assert Organization.query.count() == 1
    role_count_after_first = Role.query.count()
    user_count_after_first = User.query.count()
    assert user_count_after_first == 1

    result2 = runner.invoke(args=["init-fireflight"], env=env)
    assert result2.exit_code == 0, result2.output

    assert Organization.query.count() == 1
    assert Role.query.count() == role_count_after_first
    assert User.query.count() == user_count_after_first
