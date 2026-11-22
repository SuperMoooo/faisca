"use client";

import { useEffect } from "react";

/**
 * Registers public/sw.js, which makes Faísca installable as an app on the
 * phone and opens its pages offline. Searches always go to the network.
 * Only in production: in `next dev` a cached page would hide code changes.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Without a service worker the app still works; it only cannot be installed.
    });
  }, []);
  return null;
}
