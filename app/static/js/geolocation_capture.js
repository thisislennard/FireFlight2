document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-geolocate-target]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (!navigator.geolocation) {
        alert("Geolokalisierung wird von diesem Browser nicht unterstützt.");
        return;
      }
      var target = button.getAttribute("data-geolocate-target");
      var form = button.closest("form");
      var latInput = form.querySelector('[name="' + target + '_lat"]');
      var lonInput = form.querySelector('[name="' + target + '_lon"]');
      var originalText = button.textContent;
      button.disabled = true;
      button.textContent = "Standort wird ermittelt…";

      navigator.geolocation.getCurrentPosition(
        function (position) {
          latInput.value = position.coords.latitude;
          lonInput.value = position.coords.longitude;
          button.disabled = false;
          button.textContent = originalText;
        },
        function () {
          alert("Standort konnte nicht ermittelt werden.");
          button.disabled = false;
          button.textContent = originalText;
        }
      );
    });
  });
});
