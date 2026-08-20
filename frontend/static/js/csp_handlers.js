/**
 * ============================================================================
 * Project   : gratulo
 * Module    : frontend/static/js/csp_handlers.js
 * Purpose   : CSP-compatible replacements for former inline event handlers.
 *
 * All listeners are delegated on `document`, so they keep working for markup
 * that HTMX swaps in after the initial page load without any re-binding. This
 * lets the Content-Security-Policy drop 'unsafe-inline' from script-src.
 * ============================================================================
 */

// --- Click delegation -------------------------------------------------------
document.addEventListener("click", (e) => {
  // Remove an element by id: <button class="js-remove" data-target="modal-id">
  const remover = e.target.closest(".js-remove");
  if (remover) {
    const el = document.getElementById(remover.dataset.target);
    if (el) el.remove();
    return;
  }

  // Toggle visibility: data-hide / data-show hold space-separated element ids.
  const toggler = e.target.closest(".js-toggle");
  if (toggler) {
    (toggler.dataset.hide || "").split(/\s+/).filter(Boolean).forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.add("hidden");
    });
    (toggler.dataset.show || "").split(/\s+/).filter(Boolean).forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.remove("hidden");
    });
  }
});

// --- Change delegation ------------------------------------------------------
document.addEventListener("change", (e) => {
  const target = e.target;

  // Import preview: "show only rows with errors/warnings" checkbox.
  if (target.id === "show-only-errors") {
    const checked = target.checked;
    document.querySelectorAll("#import-form tbody tr").forEach((tr) => {
      if (checked) {
        const flagged =
          tr.classList.contains("bg-red-50") || tr.classList.contains("bg-yellow-50");
        tr.style.display = flagged ? "" : "none";
      } else {
        tr.style.display = "";
      }
    });
    return;
  }

  // Group <select>: mirror the chosen group's label into the row's hidden
  // group_name input (works for both import and sync preview rows).
  if (target.classList.contains("js-group-select")) {
    const label = target.options[target.selectedIndex].textContent.trim();
    const row = target.closest("tr");
    const nameInput = row && row.querySelector('input[name$="[group_name]"]');
    if (nameInput) nameInput.value = label;
  }
});
