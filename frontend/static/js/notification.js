export function showNotification(message, type = "error") {
  const notif = document.getElementById("notification");
  const box = document.getElementById("notification-box");
  const msg = document.getElementById("notification-message");

  msg.textContent = message;

  // Farben je nach Typ
  const base = "max-w-md w-full mx-4 px-6 py-4 rounded shadow-lg text-white text-center";
  if (type === "error") box.className = `${base} bg-red-600`;
  else if (type === "success") box.className = `${base} bg-green-600`;
  else box.className = `${base} bg-gray-800`;

  notif.classList.remove("hidden");

  // Nach 4 Sekunden wieder ausblenden
  setTimeout(() => notif.classList.add("hidden"), 4000);
}
