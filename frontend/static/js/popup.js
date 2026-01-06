/**
 * Zeigt das Bestätigungs-Modal in base.html an.
 */
export function showConfirmation(message) {
    return new Promise((resolve) => {
        // 1. IDs exakt passend zur base.html
        const modal = document.getElementById('confirmation-modal');
        const msgEl = document.getElementById('popup-message');
        const yesBtn = document.getElementById('popup-yes');
        const noBtn = document.getElementById('popup-no');

        // Sicherheitscheck: Gibt es das HTML überhaupt?
        if (!modal || !yesBtn || !noBtn) {
            console.error("❌ Modal-HTML in base.html nicht gefunden! Prüfe IDs: confirmation-modal, popup-yes");
            // Fallback auf Browser-Confirm, damit User nicht stuck ist
            resolve(confirm(message));
            return;
        }

        // 2. Text setzen
        if (msgEl) msgEl.textContent = message;

        // 3. Anzeigen
        modal.classList.remove('hidden');

        // Helper zum Schließen
        const close = () => {
            modal.classList.add('hidden');
        };

        // 4. Click Handler (nur einmalig binden bzw. überschreiben)
        yesBtn.onclick = () => {
            close();
            resolve(true);
        };

        noBtn.onclick = () => {
            close();
            resolve(false);
        };
    });
}