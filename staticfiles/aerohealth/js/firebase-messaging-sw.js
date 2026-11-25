
importScripts(
  "https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js"
);
importScripts(
  "https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js"
);

firebase.initializeApp({
  apiKey: "AIzaSyBZIKCHsxoA4QfjOjt2AC7-_ajxfyvcFU8",
  authDomain: "aerohealth-89dab.firebaseapp.com",
  projectId: "aerohealth-89dab",
  storageBucket: "aerohealth-89dab.firebasestorage.app",
  messagingSenderId: "568598842704",
  appId: "1:568598842704:web:60d19613a98230d6e33055"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  self.registration.showNotification(
    payload.notification?.title || "AeroHealth Alert",
    {
      body: payload.notification?.body || "Check your air quality.",
      icon: "/static/aerohealth/images/icon.png"
    }
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  event.waitUntil(
    clients.openWindow("/")
  );
});
