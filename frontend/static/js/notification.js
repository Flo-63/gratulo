/*!
===============================================================================
Project   : gratulo
Script    : notification.js
Created   : 05.01.2026
Author    : Florian
Purpose   : [Describe the purpose of this script.]

@docstyle: google
@language: english
@voice: imperative
===============================================================================
*/
/**
 * Zeigt eine Toast-Notification oben rechts an.
 * @param {string} message - Der Text der Nachricht
 * @param {string} type - 'success', 'error' oder 'info'
 */
export function showNotification(message, type = "info") {
    // Container prüfen oder erstellen
    let container = document.getElementById("notification-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "notification-container";
        // Tailwind Klassen für Positionierung (oben rechts)
        container.className = "fixed top-5 right-5 z-50 flex flex-col gap-2";
        document.body.appendChild(container);
    }

    // Farben basierend auf Typ
    const styles = {
        success: "bg-green-500 border-green-600",
        error: "bg-red-500 border-red-600",
        info: "bg-blue-500 border-blue-600"
    };
    const activeStyle = styles[type] || styles.info;

    // Das eigentliche Toast-Element
    const toast = document.createElement("div");
    toast.className = `${activeStyle} text-white px-6 py-3 rounded shadow-lg border-l-4 transform transition-all duration-300 translate-x-full opacity-0`;
    toast.innerText = message;

    container.appendChild(toast);

    // Animation: Einfliegen
    requestAnimationFrame(() => {
        toast.classList.remove("translate-x-full", "opacity-0");
    });

    // Nach 3 Sekunden entfernen
    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-x-full");
        setTimeout(() => {
            toast.remove();
        }, 300); // Warten bis Animation fertig ist
    }, 4000);
}