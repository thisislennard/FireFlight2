(function () {
  "use strict";

  function csrfToken() {
    try {
      return JSON.parse(document.body.getAttribute("hx-headers") || "{}")["X-CSRFToken"] || "";
    } catch (err) {
      return "";
    }
  }

  async function playWhep(video, whepUrl) {
    var pc = new RTCPeerConnection();
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });
    pc.ontrack = function (event) {
      video.srcObject = event.streams[0];
    };
    var offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    var resp = await fetch(whepUrl, {
      method: "POST",
      headers: { "Content-Type": "application/sdp" },
      body: offer.sdp,
    });
    if (!resp.ok) {
      pc.close();
      throw new Error("WHEP-Handshake fehlgeschlagen (HTTP " + resp.status + ")");
    }
    var answerSdp = await resp.text();
    await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
    return pc;
  }

  async function onStartClick(button) {
    var block = button.closest("[data-livestream-block]");
    var video = block.querySelector("video");
    var status = block.querySelector("[data-livestream-status]");

    button.disabled = true;
    status.textContent = "Starte Livestream …";

    var form = new FormData();
    form.set("sn", button.dataset.sn);
    form.set("camera_index", button.dataset.cameraIndex);
    form.set("project_uuid", button.dataset.projectUuid);

    try {
      var resp = await fetch(button.dataset.startUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: form,
      });
      var data = await resp.json();
      if (!data.ok) {
        status.textContent = "Fehler: " + (data.error || "Unbekannter Fehler");
        button.disabled = false;
        return;
      }
      if (!data.url) {
        status.textContent = data.message || "Keine Stream-URL erhalten.";
        button.disabled = false;
        return;
      }
      await playWhep(video, data.url);
      video.style.display = "block";
      status.textContent = data.expire_ts
        ? "Live — Token gültig bis " + new Date(data.expire_ts * 1000).toLocaleTimeString("de-DE")
        : "Live";
      button.textContent = "Neu starten";
      button.disabled = false;
    } catch (err) {
      status.textContent = "Fehler: " + err.message;
      button.disabled = false;
    }
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-livestream-btn]");
    if (button) {
      onStartClick(button);
    }
  });
})();
