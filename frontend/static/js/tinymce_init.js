/*
===============================================================================
Project   : gratulo
Module    : frontend/static/js/tinymce_init.js
Created   : 2025-10-20
Author    : Florian
Purpose   : Initialisierung von TinyMCE mit sicherem File Picker & Fallback-Logik

@docstyle: google
@language: german
@voice: imperative
===============================================================================
*/

document.addEventListener("DOMContentLoaded", function () {
  if (typeof tinymce === "undefined") {
    console.error("TinyMCE not found. Ensure tinymce.min.js is loaded.");
    return;
  }

  tinymce.init({
    selector: "#editor",
    height: 400,
    menubar: false,
    license_key: "gpl",
    plugins: "image link lists table code emoticons",
    toolbar:
      "undo redo | styles | bold italic underline | image | align | bullist numlist | link table | emoticons | logos | code | placeholders",
    branding: false,

    // Upload-Config
    images_upload_url: "/htmx/templates/upload-image",
    automatic_uploads: true,
    file_picker_types: "image",
    image_advtab: true,

    // Absolute URLs erzwingen
    relative_urls: false,
    remove_script_host: false,
    convert_urls: true,

    style_formats: [
      { title: "Bild mittig zum Text", selector: "img", styles: { "vertical-align": "middle" } },
      { title: "Bild oben", selector: "img", styles: { "vertical-align": "top" } },
      { title: "Bild unten", selector: "img", styles: { "vertical-align": "bottom" } },
    ],

    // ------------------------------------------
    // FILE PICKER
    // ------------------------------------------
    file_picker_callback: function (callback, value, meta) {
      if (meta.filetype === "image") {
        fetch("/htmx/templates/list-images")
          .then((res) => res.json())
          .then((images) => {
            const picker = window.open("", "Image Picker", "width=400,height=400");
            picker.document.open();
            picker.document.write("<h3>Bild auswählen</h3><div style='display:flex;flex-wrap:wrap;gap:10px;'></div>");
            const container = picker.document.querySelector("div");

            images.forEach((url) => {
              const img = picker.document.createElement("img");
              img.src = url;
              img.style.maxWidth = "120px";
              img.style.maxHeight = "120px";
              img.style.cursor = "pointer";
              img.title = url;

              img.addEventListener("click", () => {
                try {
                  // ---------------------
                  // Normaler Popup-Modus
                  // ---------------------
                  if (window.opener && typeof window.opener.postMessage === "function") {
                    window.opener.postMessage(url, "*");
                    picker.close();
                    return;
                  }

                  // ---------------------
                  // Inline-/Modal-Modus (kein window.opener)
                  // ---------------------
                  if (window.parent && window.parent.tinymce) {
                    const editor = window.parent.tinymce.activeEditor;
                    if (editor) {
                      editor.insertContent(`<img src="${url}" alt="">`);
                      // Versuch, Dialog zu schließen (TinyMCE-Modal)
                      if (editor.windowManager) {
                        try {
                          editor.windowManager.close();
                        } catch {
                          console.debug("TinyMCE windowManager.close() not available.");
                        }
                      }
                    }
                  } else {
                    console.warn("Kein Fenster-Opener und kein TinyMCE-Fenster gefunden.");
                  }

                  // ---------------------
                  // Sicheres Selbstschließen (Fallback)
                  // ---------------------
                  setTimeout(() => {
                    try {
                      picker.open("", "_self");
                      picker.close();
                    } catch (e) {
                      console.debug("Browser blockiert self-close:", e);
                    }
                  }, 200);
                } catch (e) {
                  console.error("Fehler beim Verarbeiten des Bildklicks:", e);
                }
              });

              container.appendChild(img);
            });

            picker.document.close();
          })
          .catch((err) => console.error("Fehler beim Laden der Bilder:", err));
      }
    },

    // ------------------------------------------
    // SETUP
    // ------------------------------------------
    setup: function (editor) {
      // Empfängt Bild-URLs von Pop-up Fenstern
      window.addEventListener("message", (event) => {
        if (typeof event.data === "string" && event.data.startsWith("/uploads/")) {
          editor.insertContent(`<img src="${event.data}" alt="">`);
        }
      });

      // Platzhalter-Menü
      editor.ui.registry.addMenuButton("placeholders", {
      text: "Platzhalter",
      fetch: function (callback) {
        callback([
          { type: "menuitem", text: "Vorname", onAction: () => editor.insertContent("{{Vorname}}") },
          { type: "menuitem", text: "Nachname", onAction: () => editor.insertContent("{{Nachname}}") },
          { type: "menuitem", text: "Email", onAction: () => editor.insertContent("{{Email}}") },
          { type: "menuitem", text: "Anrede (Liebe, Lieber)", onAction: () => editor.insertContent("{{Anrede}}") },
          { type: "menuitem", text: "Anrede (Sehr geehrter / Sehr geehrte)", onAction: () => editor.insertContent("{{AnredeLang}}") },
          { type: "menuitem", text: "Bezeichnung (Herr / Frau)", onAction: () => editor.insertContent("{{Bezeichnung}}") },
          { type: "menuitem", text: "Pronomen (er / sie)", onAction: () => editor.insertContent("{{Pronomen}}") },
          { type: "menuitem", text: "Possessivpronomen (sein / ihr)", onAction: () => editor.insertContent("{{Possessiv}}") },
          { type: "menuitem", text: "Geburtstag (Datum)", onAction: () => editor.insertContent("{{Geburtstag}}") },
          { type: "menuitem", text: "Wievielter Geburtstag", onAction: () => editor.insertContent("{{GeburtstagNummer}}") },
          { type: "menuitem", text: "Mitglied seit", onAction: () => editor.insertContent("{{MitgliedSeit}}") },
        ]);
      },
    });


      // Logos-Menü
     editor.ui.registry.addMenuButton("logos", {
      text: "Logos",
      fetch: function (callback) {
        callback([
          {
            type: "menuitem",
            text: "RCB-Logo weiß",
            onAction: () =>
              editor.insertContent('<img src="/static/images/logo-white-tiny.png" alt="Vereinslogo" style="max-width:200px;">'),
          },
          {
            type: "menuitem",
            text: "RCB-Logo blau",
            onAction: () =>
              editor.insertContent('<img src="/static/images/logo-blue-small.png" alt="Vereinslogo" style="max-width:200px;">'),
          },
          {
            type: "menuitem",
            text: "Banner",
            onAction: () =>
              editor.insertContent('<img src="/static/images/banner.png" alt="Banner" style="max-width:400px;">'),
          },
        ]);
      },
    });

    },
  });
});
