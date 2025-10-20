// ============================================================================
// Mail Queue Status Alpine Component
// SICHERE Initialisierung: sofort verfügbar, kein Race Condition mit Alpine.
// ============================================================================

// Direktes Setup, damit mailQueueStatus() synchron existiert
window.mailQueueStatus = function (nextRunIn = 0, queueInterval = 15, rateLimitWindow = 60) {
  return {
    seconds: nextRunIn,
    queueInterval,
    rateLimitWindow,
    timer: null,

    get progressWidth() {
      const pct = ((this.queueInterval - this.seconds) / this.queueInterval) * 100;
      return `width: ${Math.min(Math.max(pct, 0), 100)}%`;
    },

    start() {
      if (this.timer) clearInterval(this.timer);
      this.timer = setInterval(() => {
        if (this.seconds > 0) this.seconds--;
      }, 1000);
    },

    stop() {
      if (this.timer) clearInterval(this.timer);
    },

    destroy() {
      this.stop();
    },
  };
};

// --- Alpine-Integration ---
document.addEventListener("alpine:init", () => {
  if (!window.Alpine) return;
  if (!window.__MAIL_QUEUE_REGISTERED__) {
    window.Alpine.data("mailQueueStatus", window.mailQueueStatus);
    window.__MAIL_QUEUE_REGISTERED__ = true;
    console.info("[mail_queue_status] Alpine.data('mailQueueStatus') registered (sync + async)");
  }
});

// --- Synchronisierung nach HTMX-Update ---
document.addEventListener("htmx:afterOnLoad", (e) => {
  const el = document.querySelector("#job-status");
  if (!el || !el.__x) return;

  const nextRun = parseInt(el.dataset.nextRun || 0);
  const queueInt = parseInt(el.dataset.queueInterval || 15);
  const rateLimit = parseInt(el.dataset.rateLimit || 60);

  // Falls Komponente neu initialisiert werden muss
  if (!el.__x.$data || typeof el.__x.$data.seconds === "undefined") {
    window.Alpine.initTree(el);
    return;
  }

  el.__x.$data.seconds = nextRun;
  el.__x.$data.queueInterval = queueInt;
  el.__x.$data.rateLimitWindow = rateLimit;
});
