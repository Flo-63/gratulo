/*
===============================================================================
Project   : gratulo
Module    : frontend/static/js/tinymce_init.js
Created   : 2025-10-20
Author    : Florian
Purpose   : [Describe the purpose of this module.]

@docstyle: google
@language: english
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

    file_picker_callback: function (callback, value, meta) {
      if (meta.filetype === "image") {
        fetch("/htmx/templates/list-images")
          .then((res) => res.json())
          .then((images) => {
            const win = window.open("", "Image Picker", "width=400,height=400");
            win.document.open();
            win.document.write("<h3>Bild auswählen</h3>");
            images.forEach((url) => {
              const div = win.document.createElement("div");
              div.style.margin = "5px";
              div.style.cursor = "pointer";
              div.style.display = "inline-block";
              const img = win.document.createElement("img");
              img.src = url;
              img.style.maxWidth = "120px";
              img.style.maxHeight = "120px";
              img.addEventListener("click", () => {
                window.opener.postMessage(url, "*");
                win.close();
              });
              div.appendChild(img);
              win.document.body.appendChild(div);
            });
            win.document.close();
          });
      }
    },

    setup: function (editor) {
      window.addEventListener("message", (event) => {
        if (event.data.startsWith("/uploads/")) {
          editor.insertContent(`<img src="${event.data}" alt="">`);
        }
      });

      editor.ui.registry.addMenuButton("placeholders", {
        text: "Platzhalter",
        fetch: function (callback) {
          callback([
            { text: "Vorname", onAction: () => editor.insertContent("{{Vorname}}") },
            { text: "Nachname", onAction: () => editor.insertContent("{{Nachname}}") },
            { text: "Email", onAction: () => editor.insertContent("{{Email}}") },
            { text: "Anrede (Liebe, Lieber)", onAction: () => editor.insertContent("{{Anrede}}") },
            { text: "Anrede (Sehr geehrter / Sehr geehrte)", onAction: () => editor.insertContent("{{AnredeLang}}") },
            { text: "Bezeichnung (Herr / Frau)", onAction: () => editor.insertContent("{{Bezeichnung}}") },
            { text: "Pronomen (er / sie)", onAction: () => editor.insertContent("{{Pronomen}}") },
            { text: "Possessivpronomen (sein / ihr)", onAction: () => editor.insertContent("{{Possessiv}}") },
            { text: "Geburtstag (Datum)", onAction: () => editor.insertContent("{{Geburtstag}}") },
            { text: "Wievielter Geburtstag", onAction: () => editor.insertContent("{{GeburtstagNummer}}") },
            { text: "Mitglied seit", onAction: () => editor.insertContent("{{MitgliedSeit}}") },
          ]);
        },
      });

      editor.ui.registry.addMenuButton("logos", {
        text: "Logos",
        fetch: function (callback) {
          callback([
            {
              text: "RCB-Logo weiß",
              onAction: () =>
                editor.insertContent('<img src="/static/images/logo-white-tiny.png" alt="Vereinslogo" style="max-width:200px;">'),
            },
            {
              text: "RCB-Logo blau",
              onAction: () =>
                editor.insertContent('<img src="/static/images/logo-blue-small.png" alt="Vereinslogo" style="max-width:200px;">'),
            },
            {
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

