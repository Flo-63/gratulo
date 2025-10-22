/*
===============================================================================
Project   : gratulo
Module    : frontend/static/js/tinymce_init.js
Created   : 2025-10-20
Author    : Florian
Purpose   : Initialisierung von TinyMCE mit sicherem File Picker & dynamischen Platzhaltern
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

    // Upload-Konfiguration
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
                  if (window.opener && typeof window.opener.postMessage === "function") {
                    window.opener.postMessage(url, "*");
                    picker.close();
                    return;
                  }

                  if (window.parent && window.parent.tinymce) {
                    const editor = window.parent.tinymce.activeEditor;
                    if (editor) {
                      editor.insertContent(`<img src="${url}" alt="">`);
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
      // Empfang von Bild-URLs aus Popup-Fenstern
      window.addEventListener("message", (event) => {
        if (typeof event.data === "string" && event.data.startsWith("/uploads/")) {
          editor.insertContent(`<img src="${event.data}" alt="">`);
        }
      });

      // ------------------------------------------
      // Dynamische Platzhalter mit Labels aus .env
      // ------------------------------------------
      editor.ui.registry.addMenuButton("placeholders", {
          text: "Platzhalter",
          fetch: function (callback) {
            const labels = {
              date1: window.GRATULO_LABEL_DATE1 || "Geburtstag",
              date1_type: window.GRATULO_LABEL_DATE1_TYPE || "ANNIVERSARY",
              date2: window.GRATULO_LABEL_DATE2 || "Eintritt",
              date2_type: window.GRATULO_LABEL_DATE2_TYPE || "ANNIVERSARY",
              entity: window.GRATULO_LABEL_ENTITY_SINGULAR || "Mitglied",
            };

            const menu = [
              { type: "menuitem", text: "Vorname", onAction: () => editor.insertContent("{{Vorname}}") },
              { type: "menuitem", text: "Nachname", onAction: () => editor.insertContent("{{Nachname}}") },
              { type: "menuitem", text: "Email", onAction: () => editor.insertContent("{{Email}}") },
              { type: "menuitem", text: "Anrede (Liebe / Lieber)", onAction: () => editor.insertContent("{{Anrede}}") },
              { type: "menuitem", text: "Anrede (Sehr geehrter / Sehr geehrte)", onAction: () => editor.insertContent("{{AnredeLang}}") },
              { type: "menuitem", text: "Bezeichnung (Herr / Frau)", onAction: () => editor.insertContent("{{Bezeichnung}}") },
              { type: "menuitem", text: "Pronomen (er / sie)", onAction: () => editor.insertContent("{{Pronomen}}") },
              { type: "menuitem", text: "Possessivpronomen (sein / ihr)", onAction: () => editor.insertContent("{{Possessiv}}") },
            ];

            // === Dynamische Logik für DATE1 ===
            if (labels.date1_type === "ANNIVERSARY") {
              menu.push(
                { type: "menuitem", text: `${labels.date1} (Datum)`, onAction: () => editor.insertContent(`{{${labels.date1}}}`) },
                { type: "menuitem", text: `Wievielter ${labels.date1}`, onAction: () => editor.insertContent(`{{${labels.date1}Nummer}}`) }
              );
            } else {
              menu.push({ type: "menuitem", text: `${labels.date1}`, onAction: () => editor.insertContent(`{{${labels.date1}}}`) });
            }

            // === Dynamische Logik für DATE2 ===
            if (labels.date2_type === "ANNIVERSARY") {
              menu.push(
                { type: "menuitem", text: `${labels.date2} (Datum)`, onAction: () => editor.insertContent(`{{${labels.date2}}}`) },
                { type: "menuitem", text: `Wievielter ${labels.date2}`, onAction: () => editor.insertContent(`{{${labels.date2}Nummer}}`) }
              );
            } else {
              menu.push({ type: "menuitem", text: `${labels.date2}`, onAction: () => editor.insertContent(`{{${labels.date2}}}`) });
            }

            // === Entity ===
            menu.push({ type: "menuitem", text: `${labels.entity}`, onAction: () => editor.insertContent(`{{${labels.entity}}}`) });

            callback(menu);
          },
        });


      // ------------------------------------------
      // Logos-Menü (unverändert)
      // ------------------------------------------
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
