
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";

import {
  getMessaging,
  getToken,
  isSupported
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging.js";

const firebaseConfig = {
  apiKey: "AIzaSyBZIKCHsxoA4QfjOjt2AC7-_ajxfyvcFU8",
  authDomain: "aerohealth-89dab.firebaseapp.com",
  projectId: "aerohealth-89dab",
  storageBucket: "aerohealth-89dab.firebasestorage.app",
  messagingSenderId: "568598842704",
  appId: "1:568598842704:web:60d19613a98230d6e33055"
};

const VAPID_KEY = "BI53d2idxeAoKaseRCirFePjbrWe4C1q32Yk-tOVoyRmg8KEqZCyjkpfk90RNRczopZAAu5bhVtGwbhmFGv6dbQ";

const button = document.getElementById("enable-push-btn");
const status = document.getElementById("push-status");

function getCSRFToken() {
  return document.querySelector(
    'input[name="csrfmiddlewaretoken"]'
  )?.value || "";
}

if (button && status) {
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Configuring notifications...";

    try {
      if (!("serviceWorker" in navigator) ||
          !("Notification" in window)) {
        throw new Error("Browser notifications are not supported.");
      }

      if (!(await isSupported())) {
        throw new Error("Firebase Messaging is not supported.");
      }

      const permission = await Notification.requestPermission();

      if (permission !== "granted") {
        throw new Error("Notification permission was denied.");
      }

      const app = initializeApp(firebaseConfig);
      const messaging = getMessaging(app);

      const registration = await navigator.serviceWorker.register(
        "/static/firebase-messaging-sw.js"
      );

      const token = await getToken(messaging, {
        vapidKey: VAPID_KEY,
        serviceWorkerRegistration: registration
      });

      if (!token) {
        throw new Error("Unable to generate FCM device token.");
      }

      const response = await fetch("/api/alerts/settings/", {
        method: "PATCH",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken()
        },
        body: JSON.stringify({
          fcm_token: token,
          push_enabled: true
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          JSON.stringify(data)
        );
      }

      status.textContent =
        "AeroHealth browser notifications enabled successfully!";

      button.textContent = "Notifications enabled";

    } catch (error) {
      console.error("FCM registration error:", error);
      status.textContent = error.message;
      button.disabled = false;
    }
  });
}
