import { showConfirmation } from './popup.js';

// HTMX Confirmation Handler
htmx.on('htmx:confirm', function(evt) {
  evt.preventDefault();

  const confirmMessage = evt.detail.question || 'Möchten Sie fortfahren?';

  showConfirmation(confirmMessage).then((confirmed) => {
    if (confirmed) {
      evt.detail.issueRequest(true);
    }
  });
});