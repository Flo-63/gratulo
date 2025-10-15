window.mailQueueStatus = function (nextRunIn, queueInterval, rateLimitWindow) {
  return {
    nextRunIn: nextRunIn,
    queueInterval: queueInterval,
    rateLimitWindow: rateLimitWindow,
    seconds: nextRunIn,
    elapsed: queueInterval - nextRunIn,
    interval: null,

    start() {
      if (this.interval) clearInterval(this.interval);
      this.interval = setInterval(() => this.tick(), 1000);
    },

    tick() {
      if (this.seconds > 0) {
        this.seconds--;
        this.elapsed++;
      } else {
        // Zyklus abgeschlossen → nächste Queue-Runde
        this.seconds = this.queueInterval;
        this.elapsed = 0;
      }
    },

    sync(newNextRun, newQueueInterval, newRateLimit) {
      // Werte übernehmen, ohne Animation zu resetten
      this.nextRunIn = newNextRun;
      this.queueInterval = newQueueInterval;
      this.rateLimitWindow = newRateLimit;

      // Nur Sekunden neu setzen, wenn sich etwas geändert hat
      if (this.seconds !== newNextRun) {
        this.seconds = newNextRun;
        this.elapsed = Math.max(0, this.queueInterval - newNextRun);
      }
    },

    get progressWidth() {
      const pct = Math.min((this.elapsed / this.queueInterval) * 100, 100);
      return `width: ${pct}%;`;
    },
  };
};

// --- Synchronisierung nach HTMX-Update (ohne DOM-Swap!) ---
document.addEventListener("htmx:afterOnLoad", (e) => {
  const el = document.querySelector("#job-status");
  if (!el || !el.__x) return;

  const nextRun = parseInt(el.dataset.nextRun || 0);
  const queueInt = parseInt(el.dataset.queueInterval || 15);
  const rateLimit = parseInt(el.dataset.rateLimit || 60);

  el.__x.$data.sync(nextRun, queueInt, rateLimit);
});
