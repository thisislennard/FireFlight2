import uuid

from app.dashboards.models import Dashboard, DashboardWidget
from app.extensions import db


def get_or_create_dashboard(role) -> Dashboard:
    dashboard = Dashboard.query.filter_by(role_id=role.id).first()
    if dashboard is None:
        dashboard = Dashboard(
            organization_id=role.organization_id,
            role_id=role.id,
            name=f"Dashboard – {role.name}",
        )
        db.session.add(dashboard)
        db.session.commit()
    return dashboard


def add_widget(dashboard: Dashboard, *, widget_type: str, title: str | None, config: dict) -> DashboardWidget:
    position = len(dashboard.widgets)
    widget = DashboardWidget(
        dashboard_id=dashboard.id,
        widget_type=widget_type,
        title=title,
        position=position,
        config=config or {},
    )
    db.session.add(widget)
    dashboard.version += 1
    db.session.commit()
    return widget


def update_widget(widget: DashboardWidget, **fields) -> DashboardWidget:
    for key, value in fields.items():
        setattr(widget, key, value)
    widget.dashboard.version += 1
    db.session.commit()
    return widget


def remove_widget(widget: DashboardWidget) -> None:
    dashboard = widget.dashboard
    db.session.delete(widget)
    dashboard.version += 1
    db.session.commit()


def reorder_widgets(dashboard: Dashboard, ordered_widget_ids: list[uuid.UUID]) -> None:
    by_id = {w.id: w for w in dashboard.widgets}
    for index, widget_id in enumerate(ordered_widget_ids):
        widget = by_id.get(widget_id)
        if widget is not None:
            widget.position = index
    dashboard.version += 1
    db.session.commit()
