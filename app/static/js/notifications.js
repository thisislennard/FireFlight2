(function () {
  const DEFAULT_SW_URL = "/static/js/sw.js";

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]').content;
  }

  // https://developer.mozilla.org/.../PushManager/subscribe -- applicationServerKey erwartet ein
  // Uint8Array, der VAPID-Public-Key kommt vom Server aber als base64url-String.
  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`Anfrage an ${url} fehlgeschlagen (${response.status})`);
    }
    return response.json();
  }

  async function subscribeToPush(swUrl, vapidPublicKey, statusEl) {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      statusEl.textContent = "Push-Benachrichtigungen werden von diesem Browser nicht unterstützt.";
      return;
    }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      statusEl.textContent = "Berechtigung für Benachrichtigungen wurde nicht erteilt.";
      return;
    }
    const registration = await navigator.serviceWorker.register(swUrl);
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    });
    await postJson("/notifications/subscribe", subscription.toJSON());
    window.location.reload();
  }

  async function unsubscribeFromPush(swUrl, statusEl) {
    if (!("serviceWorker" in navigator)) return;
    const registration = await navigator.serviceWorker.getRegistration(swUrl);
    const subscription = registration && (await registration.pushManager.getSubscription());
    if (subscription) {
      await postJson("/notifications/unsubscribe", { endpoint: subscription.endpoint });
      await subscription.unsubscribe();
    }
    window.location.reload();
  }

  // Nur für Kontexte ohne eigenes <form>-Postback (z. B. der RC-Kiosk-Zugang, app/rc/home.html) --
  // die Desktop-Einstellungsseite nutzt stattdessen ein normales Formular, weil sie ohnehin auf sich
  // selbst zurück-redirected. `/notifications/test-send` liefert bei Accept: application/json eine
  // JSON-Antwort statt Redirect+Flash (app/notifications/routes.py: Content Negotiation).
  async function testSend(statusEl) {
    const response = await fetch("/notifications/test-send", {
      method: "POST",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken() },
    });
    const payload = await response.json();
    statusEl.textContent = payload.message;
  }

  document.addEventListener("DOMContentLoaded", () => {
    const subscribeBtn = document.getElementById("notifications-subscribe");
    const unsubscribeBtn = document.getElementById("notifications-unsubscribe");
    const testSendBtn = document.getElementById("notifications-test-send");
    const statusEl = document.getElementById("notifications-status");
    const swUrl = (subscribeBtn && subscribeBtn.dataset.swUrl) || DEFAULT_SW_URL;

    if (subscribeBtn) {
      subscribeBtn.addEventListener("click", () => {
        subscribeToPush(swUrl, subscribeBtn.dataset.vapidPublicKey, statusEl).catch((err) => {
          statusEl.textContent = err.message;
        });
      });
    }
    if (unsubscribeBtn) {
      unsubscribeBtn.addEventListener("click", () => {
        unsubscribeFromPush(swUrl, statusEl).catch((err) => {
          statusEl.textContent = err.message;
        });
      });
    }
    if (testSendBtn) {
      testSendBtn.addEventListener("click", () => {
        testSend(statusEl).catch((err) => {
          statusEl.textContent = err.message;
        });
      });
    }
  });
})();
