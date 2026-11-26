const firebaseConfig = {
  apiKey: "AIzaSyBZIKCHsxoA4QfjOjt2AC7-_ajxfyvcFU8",
  authDomain: "aerohealth-89dab.firebaseapp.com",
  projectId: "aerohealth-89dab",
  storageBucket: "aerohealth-89dab.firebasestorage.app",
  messagingSenderId: "568598842704",
  appId: "1:568598842704:web:60d19613a98230d6e33055"
};

const VAPID_KEY =
  "BI53d2idxeAoKaseRCirFePjbrWe4C1q32Yk-tOVoyRmg8KEqZCyjkpfk90RNRczopZAAu5bhVtGwbhmFGv6dbQ";

const button = document.getElementById("enable-push-btn");
const status = document.getElementById("push-status");

function getCSRFToken() {
  return document.querySelector(
    'input[name="csrfmiddlewaretoken"]'
  )?.value || "";
}

function waitForActiveServiceWorker(registration) {
  const worker =
    registration.installing ||
    registration.waiting ||
    registration.active;

  if (!worker) {
    return Promise.reject(new Error("No service worker found."));
  }

  if (worker.state === "activated") {
    return Promise.resolve(registration);
  }

  return new Promise((resolve, reject) => {
    function checkState() {
      if (worker.state === "activated") {
        worker.removeEventListener("statechange", checkState);
        resolve(registration);
      } else if (worker.state === "redundant") {
        worker.removeEventListener("statechange", checkState);
        reject(new Error("Service worker installation failed."));
      }
    }

    worker.addEventListener("statechange", checkState);
    checkState();
  });
}

if (button && status) {
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Configuring notifications...";

    try {
      if (!window.isSecureContext) {
        throw new Error(
          "Browser notifications require HTTPS (localhost is supported)."
        );
      }

      if (!("serviceWorker" in navigator) || !("Notification" in window)) {
        throw new Error("Browser notifications are not supported.");
      }

      if (Notification.permission === "denied") {
        throw new Error(
          "Notifications are blocked for this site. Allow them in your browser's site settings, then reload."
        );
      }

      // Request permission immediately within the button click handler.
      status.textContent = "Requesting notification permission...";
      const permission = await Notification.requestPermission();

      if (permission !== "granted") {
        throw new Error("Notification permission was not granted.");
      }

      const [
        { getApp, getApps, initializeApp },
        { getMessaging, getToken, isSupported }
      ] = await Promise.all([
        import("https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js"),
        import("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging.js")
      ]);

      if (!(await isSupported())) {
        throw new Error(
          "Firebase Messaging is not supported in this browser."
        );
      }

      const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
      const messaging = getMessaging(app);

      const registration = await navigator.serviceWorker.register(
        "/static/firebase-messaging-sw.js"
      );

      status.textContent = "Activating notification service...";
      const activeRegistration =
        await waitForActiveServiceWorker(registration);

      status.textContent = "Generating device token...";
      const token = await getToken(messaging, {
        vapidKey: VAPID_KEY,
        serviceWorkerRegistration: activeRegistration
      });

      if (!token) {
        throw new Error("Unable to generate an FCM device token.");
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
        throw new Error(JSON.stringify(data));
      }

      status.textContent =
        "AeroHealth browser notifications enabled successfully!";
      button.textContent = "Notifications enabled";
    } catch (error) {
      console.error("FCM registration error:", error);
      status.textContent =
        error instanceof Error ? error.message : "Could not enable notifications.";
      button.disabled = false;
    }
  });
}