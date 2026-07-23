from werkzeug.datastructures import MultiDict

from app.core.exceptions import ValidationError
from app.extensions import db
from app.wizards.models import Wizard, WizardStep
from app.wizards.runner import WizardRunner
from app.wizards.services import (
    activate_wizard,
    add_step,
    config_from_form,
    create_wizard,
    deactivate_wizard,
    delete_step,
    list_wizards,
    move_step,
    update_step,
    update_wizard,
)
from app.wizards.step_types import step_type_registry
from tests.conftest import login


# --- Step-Type-Registry ------------------------------------------------------------------------


def test_info_step_always_valid():
    definition = step_type_registry.get("info")
    answer = definition.parse_answer(MultiDict(), {"body": "Hallo"})
    assert definition.validate({"body": "Hallo"}, answer) is True


def test_checklist_requires_all_items_checked():
    definition = step_type_registry.get("checklist")
    config = {"items": ["A", "B", "C"]}
    partial = definition.parse_answer(MultiDict([("answer_items", "0"), ("answer_items", "1")]), config)
    assert definition.validate(config, partial) is False
    full = definition.parse_answer(
        MultiDict([("answer_items", "0"), ("answer_items", "1"), ("answer_items", "2")]), config
    )
    assert definition.validate(config, full) is True


def test_checklist_with_no_items_is_trivially_valid():
    definition = step_type_registry.get("checklist")
    answer = definition.parse_answer(MultiDict(), {"items": []})
    assert definition.validate({"items": []}, answer) is True


def test_confirmation_requires_checkbox():
    definition = step_type_registry.get("confirmation")
    unchecked = definition.parse_answer(MultiDict(), {"label": "x"})
    assert definition.validate({"label": "x"}, unchecked) is False
    checked = definition.parse_answer(MultiDict([("answer", "on")]), {"label": "x"})
    assert definition.validate({"label": "x"}, checked) is True


def test_text_input_required_rejects_empty():
    definition = step_type_registry.get("text_input")
    config = {"label": "Zweck", "required": True}
    empty = definition.parse_answer(MultiDict([("answer", "  ")]), config)
    assert definition.validate(config, empty) is False
    filled = definition.parse_answer(MultiDict([("answer", "Übung")]), config)
    assert definition.validate(config, filled) is True


def test_text_input_not_required_accepts_empty():
    definition = step_type_registry.get("text_input")
    config = {"label": "Notiz", "required": False}
    answer = definition.parse_answer(MultiDict(), config)
    assert definition.validate(config, answer) is True


def test_choice_requires_known_option():
    definition = step_type_registry.get("choice")
    config = {"label": "Typ", "options": ["Einsatz", "Übung"]}
    invalid = definition.parse_answer(MultiDict([("answer", "Sonstiges")]), config)
    assert definition.validate(config, invalid) is False
    valid = definition.parse_answer(MultiDict([("answer", "Einsatz")]), config)
    assert definition.validate(config, valid) is True


def test_config_from_form_parses_lines_and_bool():
    form = MultiDict([("label", "Zweck"), ("required", "on")])
    config = config_from_form("text_input", form)
    assert config == {"label": "Zweck", "required": True}

    form2 = MultiDict([("items", "Punkt 1\nPunkt 2\n\n  Punkt 3  ")])
    config2 = config_from_form("checklist", form2)
    assert config2 == {"items": ["Punkt 1", "Punkt 2", "Punkt 3"]}


# --- Services -----------------------------------------------------------------------------------


def test_create_wizard_rejects_duplicate_key(app, organization):
    create_wizard(organization.id, key="dup", name="Erster")
    try:
        create_wizard(organization.id, key="dup", name="Zweiter")
        assert False, "sollte ValidationError werfen"
    except ValidationError:
        pass


def test_add_step_appends_and_orders_by_position(app, organization):
    wizard = create_wizard(organization.id, key="w1", name="W1")
    s1 = add_step(wizard, step_type="info", title="A", config={"body": ""})
    s2 = add_step(wizard, step_type="info", title="B", config={"body": ""})
    db.session.refresh(wizard)
    assert [s.title for s in wizard.steps] == ["A", "B"]
    assert s1.position == 0 and s2.position == 1


def test_move_step_swaps_with_neighbor(app, organization):
    wizard = create_wizard(organization.id, key="w2", name="W2")
    s1 = add_step(wizard, step_type="info", title="A", config={"body": ""})
    s2 = add_step(wizard, step_type="info", title="B", config={"body": ""})
    move_step(s2, "up")
    db.session.refresh(wizard)
    assert [s.title for s in sorted(wizard.steps, key=lambda s: s.position)] == ["B", "A"]

    # s2 steht jetzt an erster Stelle -- "up" hat dort keinen Effekt, kein Fehler.
    move_step(s2, "up")
    db.session.refresh(wizard)
    assert [s.title for s in sorted(wizard.steps, key=lambda s: s.position)] == ["B", "A"]

    # s1 steht jetzt an letzter Stelle -- "down" hat dort keinen Effekt, kein Fehler.
    move_step(s1, "down")
    db.session.refresh(wizard)
    assert [s.title for s in sorted(wizard.steps, key=lambda s: s.position)] == ["B", "A"]


def test_delete_step_removes_it(app, organization):
    wizard = create_wizard(organization.id, key="w3", name="W3")
    step = add_step(wizard, step_type="info", title="A", config={"body": ""})
    delete_step(step)
    assert db.session.get(WizardStep, step.id) is None


def test_list_wizards_orders_by_name(app, organization):
    create_wizard(organization.id, key="z", name="Z-Wizard")
    create_wizard(organization.id, key="a", name="A-Wizard")
    names = [w.name for w in list_wizards(organization.id)]
    assert names == ["A-Wizard", "Z-Wizard"]


def test_update_wizard_changes_fields(app, organization):
    wizard = create_wizard(organization.id, key="upd", name="Alt")
    update_wizard(wizard, name="Neu", description="Beschreibung")
    db.session.refresh(wizard)
    assert wizard.name == "Neu"
    assert wizard.description == "Beschreibung"


def test_activate_deactivate_wizard(app, organization):
    wizard = create_wizard(organization.id, key="actdeact", name="AD")
    deactivate_wizard(wizard)
    assert wizard.is_active is False
    activate_wizard(wizard)
    assert wizard.is_active is True


def test_update_step_changes_title_and_config(app, organization):
    wizard = create_wizard(organization.id, key="stepupd", name="StepUpd")
    step = add_step(wizard, step_type="text_input", title="Alt", config={"label": "", "required": True})
    update_step(step, title="Neu", config={"label": "Zweck", "required": False})
    db.session.refresh(step)
    assert step.title == "Neu"
    assert step.config == {"label": "Zweck", "required": False}


# --- WizardRunner ---------------------------------------------------------------------------------


def _build_wizard(organization):
    wizard = create_wizard(organization.id, key="runner_test", name="Runner-Test")
    add_step(wizard, step_type="info", title="Info", config={"body": "Hallo"})
    add_step(wizard, step_type="checklist", title="Check", config={"items": ["a", "b"]})
    add_step(wizard, step_type="confirmation", title="Confirm", config={"label": "Ok?"})
    db.session.refresh(wizard)
    return wizard


def test_runner_advances_only_on_valid_submit(app, organization):
    wizard = _build_wizard(organization)
    runner = WizardRunner(wizard, {})

    assert runner.current_step.title == "Info"
    assert runner.submit(MultiDict()) is True
    assert runner.current_step.title == "Check"

    assert runner.submit(MultiDict([("answer_items", "0")])) is False  # nur 1 von 2 angehakt
    assert runner.current_step.title == "Check"

    assert runner.submit(MultiDict([("answer_items", "0"), ("answer_items", "1")])) is True
    assert runner.current_step.title == "Confirm"

    assert runner.submit(MultiDict()) is False  # Checkbox nicht gesetzt
    assert runner.submit(MultiDict([("answer", "on")])) is True
    assert runner.is_finished is True
    assert runner.current_step is None


def test_runner_back_and_reset(app, organization):
    wizard = _build_wizard(organization)
    runner = WizardRunner(wizard, {})
    runner.submit(MultiDict())
    assert runner.current_step.title == "Check"

    runner.back()
    assert runner.current_step.title == "Info"

    runner.back()  # am Anfang: bleibt bei 0, kein Fehler
    assert runner.current_step.title == "Info"

    runner.submit(MultiDict())
    runner.reset()
    assert runner.current_step.title == "Info"
    assert runner.state["answers"] == {}


def test_runner_stores_answers_keyed_by_step_id(app, organization):
    wizard = _build_wizard(organization)
    info_step = wizard.steps[0]
    runner = WizardRunner(wizard, {})
    runner.submit(MultiDict())
    assert str(info_step.id) in runner.state["answers"]


def test_runner_skips_inactive_steps(app, organization):
    wizard = _build_wizard(organization)
    wizard.steps[1].is_active = False  # Checklist deaktiviert
    db.session.commit()
    runner = WizardRunner(wizard, {})
    assert len(runner.steps) == 2
    runner.submit(MultiDict())
    assert runner.current_step.title == "Confirm"


# --- Admin-Routen ----------------------------------------------------------------------------


def test_admin_can_create_wizard_and_add_steps(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post("/administration/wizards/new", data={"key": "test_wiz", "name": "Testwizard"})
    assert response.status_code == 302

    wizard = Wizard.query.filter_by(key="test_wiz").first()
    assert wizard is not None

    response = client.post(
        f"/administration/wizards/{wizard.id}/steps", data={"step_type": "info", "title": "Erster Schritt"}
    )
    assert response.status_code == 302

    db.session.refresh(wizard)
    assert len(wizard.steps) == 1
    assert wizard.steps[0].title == "Erster Schritt"


def test_admin_editing_step_updates_config(client, admin_user, roles, organization):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    wizard = create_wizard(organization.id, key="cfgtest", name="Cfg")
    step = add_step(wizard, step_type="checklist", title="Checkliste", config={"items": []})

    response = client.post(
        f"/administration/wizards/{wizard.id}/steps/{step.id}",
        data={"title": "Neue Checkliste", "items": "Punkt 1\nPunkt 2"},
    )
    assert response.status_code == 302
    db.session.refresh(step)
    assert step.title == "Neue Checkliste"
    assert step.config == {"items": ["Punkt 1", "Punkt 2"]}


def test_admin_can_delete_and_move_steps(client, admin_user, roles, organization):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    wizard = create_wizard(organization.id, key="movetest", name="Move")
    s1 = add_step(wizard, step_type="info", title="A", config={"body": ""})
    s2 = add_step(wizard, step_type="info", title="B", config={"body": ""})

    client.post(f"/administration/wizards/{wizard.id}/steps/{s2.id}/move", data={"direction": "up"})
    db.session.refresh(wizard)
    assert [s.title for s in sorted(wizard.steps, key=lambda s: s.position)] == ["B", "A"]

    client.post(f"/administration/wizards/{wizard.id}/steps/{s1.id}/delete")
    db.session.refresh(wizard)
    assert len(wizard.steps) == 1


def test_admin_can_toggle_wizard_active(client, admin_user, roles, organization):
    wizard = create_wizard(organization.id, key="toggletest", name="Toggle")
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(f"/administration/wizards/{wizard.id}/toggle-active")
    assert response.status_code == 302
    db.session.refresh(wizard)
    assert wizard.is_active is False


def test_non_admin_without_permission_gets_403_on_wizards(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights_wiz", email="norights_wiz@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = [roles["documentation"]]
    db.session.commit()

    login(client, username="norights_wiz")
    client.post(f"/roles/activate/{roles['documentation'].id}")
    response = client.get("/administration/wizards")
    assert response.status_code == 403


# --- Admin-Vorschau (Preview) ------------------------------------------------------------------


def test_preview_full_walkthrough_and_completion(client, app, admin_user, roles, organization):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    wizard = _build_wizard(organization)

    get_response = client.get(f"/administration/wizards/{wizard.id}/preview")
    assert get_response.status_code == 200
    assert "Info" in get_response.get_data(as_text=True)

    step1 = client.post(f"/administration/wizards/{wizard.id}/preview", data={"action": "next"})
    assert step1.status_code == 302

    invalid = client.post(
        f"/administration/wizards/{wizard.id}/preview",
        data={"action": "next", "answer_items": "0"},
    )
    assert invalid.status_code == 200
    assert "erforderlich" in invalid.get_data(as_text=True)

    valid = client.post(
        f"/administration/wizards/{wizard.id}/preview",
        data={"action": "next", "answer_items": ["0", "1"]},
    )
    assert valid.status_code == 302

    final = client.post(
        f"/administration/wizards/{wizard.id}/preview", data={"action": "next", "answer": "on"}
    )
    assert final.status_code == 302

    done = client.get(f"/administration/wizards/{wizard.id}/preview")
    assert "Abgeschlossen" in done.get_data(as_text=True)

    reset_response = client.post(f"/administration/wizards/{wizard.id}/preview", data={"action": "reset"})
    assert reset_response.status_code == 302
    after_reset = client.get(f"/administration/wizards/{wizard.id}/preview")
    assert "Info" in after_reset.get_data(as_text=True)


def test_preview_back_action(client, app, admin_user, roles, organization):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    wizard = _build_wizard(organization)

    client.post(f"/administration/wizards/{wizard.id}/preview", data={"action": "next"})
    back = client.post(f"/administration/wizards/{wizard.id}/preview", data={"action": "back"})
    assert back.status_code == 302
    page = client.get(f"/administration/wizards/{wizard.id}/preview")
    assert "Schritt 1 von 3" in page.get_data(as_text=True)


# --- CLI: seed-test-data -------------------------------------------------------------------------


def test_seed_test_data_creates_example_wizard_with_five_steps(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["init-fireflight"], env={"FIREFLIGHT_ADMIN_PIN": "4726"})

    result1 = runner.invoke(args=["seed-test-data"])
    assert result1.exit_code == 0, result1.output
    wizard = Wizard.query.filter_by(key="beispiel_wizard").first()
    assert wizard is not None
    assert len(wizard.steps) == 5
    assert {s.step_type for s in wizard.steps} == {"info", "checklist", "choice", "text_input", "confirmation"}

    result2 = runner.invoke(args=["seed-test-data"])
    assert result2.exit_code == 0, result2.output
    assert Wizard.query.filter_by(key="beispiel_wizard").count() == 1
