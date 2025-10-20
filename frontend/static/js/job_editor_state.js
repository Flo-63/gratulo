/*
===============================================================================
Project   : gratulo
Module    : frontend/static/js/job_editor_state.js
Created   : 2025-10-20
Author    : Florian
Purpose   : [Describe the purpose of this module.]

@docstyle: google
@language: english
@voice: imperative
===============================================================================
*/

window.jobEditorState = function(modeInit, cron) {
  return {
    mode: modeInit || "regular",
    intervalType: "daily",
    init() {
      if (!cron) return;
      const parts = cron.trim().split(/\s+/);
      if (parts.length < 5) return;
      const m = parts[0], h = parts[1], dom = parts[2], dow = parts[4];

      const hh = String(parseInt(h || "6", 10)).padStart(2, "0");
      const mm = String(parseInt(m || "0", 10)).padStart(2, "0");
      const timeEl = document.querySelector('input[name="time"]');
      if (timeEl) timeEl.value = `${hh}:${mm}`;

      if (dom && dom !== "*" && !Number.isNaN(parseInt(dom, 10))) {
        this.intervalType = "monthly";
        const mdEl = document.querySelector('input[name="monthday"]');
        if (mdEl) mdEl.value = String(parseInt(dom, 10));
      } else if (dow && dow !== "*" && !Number.isNaN(parseInt(dow, 10))) {
        this.intervalType = "weekly";
        const wdEl = document.querySelector('select[name="weekday"]');
        if (wdEl) wdEl.value = String(parseInt(dow, 10));
      } else {
        this.intervalType = "daily";
      }
    },
  };
};