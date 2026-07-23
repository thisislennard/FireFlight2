from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.notifications.service import active_subscriptions_for_user, send_to_user, subscribe, unsubscribe

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


def _wants_json() -> bool:
    return request.accept_mimetypes["application/json"] >= request.accept_mimetypes["text/html"]


@bp.route("/settings")
@login_required
def settings():
    return render_template(
        "notifications/settings.html",
        subscriptions=active_subscriptions_for_user(current_user),
        vapid_public_key=current_app.config["VAPID_PUBLIC_KEY"],
    )


@bp.route("/subscribe", methods=["POST"])
@login_required
def subscribe_route():
    payload = request.get_json(silent=True) or {}
    keys = payload.get("keys") or {}
    endpoint = payload.get("endpoint")
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not endpoint or not p256dh or not auth:
        return jsonify({"error": "Unvollständige Subscription-Daten."}), 400
    subscribe(
        current_user,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=request.headers.get("User-Agent"),
    )
    return jsonify({"status": "subscribed"})


@bp.route("/unsubscribe", methods=["POST"])
@login_required
def unsubscribe_route():
    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    if not endpoint:
        return jsonify({"error": "endpoint fehlt."}), 400
    removed = unsubscribe(current_user, endpoint)
    return jsonify({"status": "unsubscribed" if removed else "not_found"})


@bp.route("/test-send", methods=["POST"])
@login_required
def test_send():
    try:
        logs = send_to_user(
            current_user,
            title="FireFlight2-Testbenachrichtigung",
            body="Wenn du das siehst, funktioniert Web-Push auf diesem Gerät.",
        )
    except ValidationError as exc:
        category, message = "error", exc.message
    else:
        if not logs:
            category, message = "error", "Kein aktives Gerät für Push-Benachrichtigungen registriert."
        elif any(log.status == "sent" for log in logs):
            category, message = "success", "Testbenachrichtigung gesendet."
        else:
            category, message = "error", "Zustellung fehlgeschlagen -- Details unten im Verlauf."

    # Content Negotiation statt eigener Route: der RC-Kiosk-Zugang (app/rc/) ruft denselben Endpunkt
    # per fetch() mit Accept: application/json auf, um ohne HTML-Redirect/Flash-Rendering auszukommen.
    if _wants_json():
        return jsonify({"status": category, "message": message})
    flash(message, category)
    return redirect(url_for("notifications.settings"))
