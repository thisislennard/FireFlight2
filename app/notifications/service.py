from __future__ import annotations

import json

import requests
from flask import current_app
from pywebpush import WebPushException, webpush

from app.core.exceptions import ValidationError
from app.core.models import utcnow
from app.extensions import db
from app.notifications.models import NotificationLog, PushSubscription


def _ensure_vapid_configured() -> None:
    if not current_app.config.get("VAPID_PRIVATE_KEY") or not current_app.config.get("VAPID_PUBLIC_KEY"):
        raise ValidationError(
            "VAPID-Schlüssel sind nicht konfiguriert. Mit `flask notifications generate-vapid-keys` "
            "erzeugen und als VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY setzen."
        )


def subscribe(user, *, endpoint: str, p256dh: str, auth: str, user_agent: str | None = None) -> PushSubscription:
    """Upsert auf `endpoint` -- derselbe Browser bleibt bei erneutem Subscribe (z. B. nach Ablauf,
    oder wenn auf einem RC-Gerät ein anderer Bediener sich einloggt) dieselbe Zeile."""
    # user.id VOR dem Anlegen der (noch unvollständigen) Subscription-Zeile lesen: ist `user` durch
    # ein vorheriges commit() expired, würde der Attributzugriff selbst einen Autoflush auslösen und
    # die bereits per add() angehängte, aber noch nicht vollständig befüllte Zeile vorzeitig
    # einfügen (NOT-NULL-Verletzung auf user_id).
    user_id = user.id
    subscription = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if subscription is None:
        subscription = PushSubscription(endpoint=endpoint)
        db.session.add(subscription)
    subscription.user_id = user_id
    subscription.p256dh = p256dh
    subscription.auth = auth
    subscription.user_agent = user_agent
    subscription.is_active = True
    subscription.last_seen_at = utcnow()
    db.session.commit()
    return subscription


def unsubscribe(user, endpoint: str) -> bool:
    """Löscht nur Subscriptions des anfragenden Nutzers -- verhindert, dass ein Nutzer per erratener
    Endpoint-URL die Subscription eines anderen Kontos entfernen kann."""
    subscription = PushSubscription.query.filter_by(endpoint=endpoint, user_id=user.id).first()
    if subscription is None:
        return False
    db.session.delete(subscription)
    db.session.commit()
    return True


def active_subscriptions_for_user(user) -> list[PushSubscription]:
    return PushSubscription.query.filter_by(user_id=user.id, is_active=True).order_by(
        PushSubscription.last_seen_at.desc()
    ).all()


def _deliver(subscription: PushSubscription, *, title: str, body: str, data: dict | None) -> NotificationLog:
    log = NotificationLog(
        user_id=subscription.user_id,
        subscription_id=subscription.id,
        title=title,
        body=body,
        data=data or {},
    )
    payload = json.dumps({"title": title, "body": body, "data": data or {}})
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=current_app.config["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": f"mailto:{current_app.config['VAPID_CLAIMS_EMAIL']}"},
            timeout=10,
        )
        log.status = "sent"
    except WebPushException as exc:
        response = exc.response
        if response is not None and response.status_code in (404, 410):
            # Push-Dienst kennt die Subscription nicht mehr (Browser-Deinstallation, abgelaufen o.ä.)
            # -- deaktivieren statt bei jedem künftigen Send erneut zu scheitern.
            subscription.is_active = False
            log.status = "expired"
        else:
            log.status = "failed"
        log.error_message = str(exc)
    except requests.exceptions.RequestException as exc:
        # Netzwerkfehler (Endpoint nicht erreichbar, Timeout, ...) statt einer regulären HTTP-Antwort
        # des Push-Diensts -- kein eindeutiges "gone"-Signal, Subscription bleibt daher aktiv.
        log.status = "failed"
        log.error_message = str(exc)
    db.session.add(log)
    db.session.commit()
    return log


def send_to_user(user, *, title: str, body: str, data: dict | None = None) -> list[NotificationLog]:
    _ensure_vapid_configured()
    subscriptions = active_subscriptions_for_user(user)
    return [_deliver(subscription, title=title, body=body, data=data) for subscription in subscriptions]


def send_to_users(users, *, title: str, body: str, data: dict | None = None) -> list[NotificationLog]:
    logs: list[NotificationLog] = []
    for user in users:
        logs.extend(send_to_user(user, title=title, body=body, data=data))
    return logs


def send_to_role(role, *, title: str, body: str, data: dict | None = None) -> list[NotificationLog]:
    return send_to_users(role.users, title=title, body=body, data=data)
