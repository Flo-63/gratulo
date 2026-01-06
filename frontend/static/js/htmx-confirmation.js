import { showConfirmation } from "./popup.js";

// Wir nutzen einen Event-Listener auf dem Body, das ist am sichersten
document.body.addEventListener('htmx:confirm', function(evt) {
    const el = evt.target; // Das Element, das geklickt wurde

    // 1. Prüfen: Hat das Element überhaupt hx-confirm?
    // Wenn nicht, lassen wir HTMX einfach weitermachen.
    if (!el.hasAttribute('hx-confirm')) {
        return;
    }

    // 2. Opt-Out Check (_no_confirm)
    // Wir lesen die URL direkt aus den Attributen, da das Event-Objekt hier oft leer ist.
    // Das behebt den "reading 'path' of undefined" Fehler.
    const url = el.getAttribute('hx-get') ||
                el.getAttribute('hx-post') ||
                el.getAttribute('hx-delete') ||
                el.getAttribute('hx-patch') ||
                el.getAttribute('hx-put') || "";

    // Wenn der "Geheimcode" in der URL steckt -> Kein Popup
    if (url.includes("_no_confirm=1")) {
        return;
    }

    // 3. HTMX stoppen (damit der Request nicht sofort rausgeht)
    evt.preventDefault();

    // 4. Frage holen (aus dem hx-confirm Attribut)
    const question = el.getAttribute('hx-confirm') || "Wirklich durchführen?";

    // 5. Modal anzeigen
    showConfirmation(question).then((confirmed) => {
        if (confirmed) {
            // Wenn User "Ja" klickt -> HTMX Request manuell fortsetzen
            // issueRequest(true) überspringt die Bestätigungs-Prüfung beim zweiten Mal
            evt.detail.issueRequest(true);
        }
    });
});