import { showNotification } from "./notification.js";

// Wenn HTMX Inhalte ersetzt oder neu lädt:
document.body.addEventListener("htmx:afterSwap", (e) => {
  if (window.Alpine) {
    window.Alpine.flushAndStopDeferringMutations();
    window.Alpine.initTree(e.target);
  }
});

// Globale htmx Fehlerbehandlung
document.body.addEventListener("htmx:responseError", function (evt) {
  let msg = "Unbekannter Fehler";
  try {
    const data = JSON.parse(evt.detail.xhr.responseText);
    msg = data.detail || JSON.stringify(data);
  } catch {
    msg = evt.detail.xhr.responseText;
  }
  showNotification(msg, "error");
});

// Erfolgsmeldungen
document.body.addEventListener("htmx:afterRequest", function (evt) {
  if (evt.detail.xhr.status >= 200 && evt.detail.xhr.status < 300) {
    if (evt.detail.elt.getAttribute("hx-show-success") !== null) {
      showNotification("Aktion erfolgreich!", "success");
    }
  }
});

