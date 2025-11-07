
/*!
===============================================================================
Project   : gratulo
Script    : popup.js
Created   : 07.11.2025
Author    : Florian
Purpose   : Elegant popup system with blur, glassy yellow dialog and white buttons.
===============================================================================
*/

const STYLES = {
  success: 'bg-green-600 text-white',
  error: 'bg-red-600 text-white',
  warning: 'bg-yellow-400 text-gray-900',
  info: 'bg-blue-600 text-white',
  confirm:
    // Kräftiges Gelb mit Shadow
    'bg-yellow-400 text-gray-900 ring-2 ring-yellow-500 shadow-2xl'
};

export function showNotification(message, type = 'info', duration = 3000) {
  const popup = document.getElementById('popup');
  const popupBox = document.getElementById('popup-box');
  const popupMessage = document.getElementById('popup-message');
  const popupButtons = document.getElementById('popup-buttons');

  // Text & Stil
  popupMessage.textContent = message;
  popupButtons.classList.add('hidden');
  popupBox.className = `
    max-w-md w-full mx-4 px-6 py-5 rounded-xl shadow-lg text-center
    ${STYLES[type] || STYLES.info}
  `;

  // Zeigen (mit Fade)
  popup.classList.remove('hidden');
  requestAnimationFrame(() => popup.classList.remove('opacity-0'));

  setTimeout(() => {
    popup.classList.add('opacity-0');
    setTimeout(() => popup.classList.add('hidden'), 200);
  }, duration);
}

export function showConfirmation(message) {
  return new Promise((resolve) => {
    const popup = document.getElementById('popup');
    const popupBox = document.getElementById('popup-box');
    const popupMessage = document.getElementById('popup-message');
    const popupButtons = document.getElementById('popup-buttons');
    const yesBtn = document.getElementById('popup-yes');
    const noBtn = document.getElementById('popup-no');

    // Stil des Dialogs (kräftiges Gelb)
    popupBox.className = `
      max-w-md w-full mx-4 px-6 py-5 rounded-xl shadow-xl text-center
      ${STYLES.confirm}
    `;

    // Buttons schöner anordnen
    popupButtons.classList.remove('hidden');
    popupButtons.classList.add('gap-6', 'mt-4');

    // Beschriftung
    popupMessage.textContent = message;

    // Button-Styling aktualisieren
    yesBtn.className =
      'bg-green-600 hover:bg-green-700 text-white font-semibold px-5 py-2 rounded-lg shadow';
    noBtn.className =
      'bg-gray-600 hover:bg-gray-700 text-white font-semibold px-5 py-2 rounded-lg shadow';

    // Zeigen (mit Fade)
    popup.classList.remove('hidden');
    requestAnimationFrame(() => popup.classList.remove('opacity-0'));

    const cleanup = () => {
      popup.classList.add('opacity-0');
      setTimeout(() => {
        popup.classList.add('hidden');
        yesBtn.removeEventListener('click', handleYes);
        noBtn.removeEventListener('click', handleNo);
      }, 200);
    };

    const handleYes = () => {
      cleanup();
      // Resolve erst nach der Fade-Out-Animation (250ms statt 200ms für etwas Buffer)
      setTimeout(() => resolve(true), 250);
    };

    const handleNo = () => {
      cleanup();
      // Resolve erst nach der Fade-Out-Animation
      setTimeout(() => resolve(false), 250);
    };

    yesBtn.addEventListener('click', handleYes);
    noBtn.addEventListener('click', handleNo);
  });
}

// Global verfügbar machen
window.showNotification = showNotification;
window.showConfirmation = showConfirmation;