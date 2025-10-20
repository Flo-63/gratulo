document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("template-form");

  if (!form) return;

  // Wenn Formular abgeschickt wird (egal ob HTMX oder klassisch)
  form.addEventListener("submit", () => {
    if (window.tinymce) tinymce.triggerSave();
  });

  // Falls HTMX-Events verwendet werden
  document.body.addEventListener("htmx:beforeRequest", (e) => {
    if (e.target === form && window.tinymce) {
      tinymce.triggerSave();
    }
  });
});

