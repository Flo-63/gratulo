// =======================================================================
// Globale Bestätigungs-Logik für HTMX Requests – mit Opt-Out Mechanismus
// =======================================================================

htmx.on('htmx:confirm', function (evt) {
  // ------------------------------------------
  // 1️⃣ Sortier-Requests erkennen und ignorieren
  // ------------------------------------------
  const url = evt.detail.requestConfig.path || "";

  // Wenn der Request dieses Flag enthält → KEINE Bestätigung anzeigen
  if (url.includes("_no_confirm=1")) {
    return; // Nichts tun → Sortierung läuft ohne Popup
  }

  // ------------------------------------------
  // 2️⃣ Normale Confirmation-Logik (dein Popup)
  // ------------------------------------------
  evt.preventDefault();

  const confirmMessage = evt.detail.question || "Möchten Sie fortfahren?";

  // showConfirmation() kommt aus popup.js
  showConfirmation(confirmMessage)
    .then((confirmed) => {
      if (confirmed) {
        evt.detail.issueRequest(true);
      }
    });
});
