import type { MetadataRoute } from "next";

// Rendered once at build time into manifest.webmanifest (the export has no server).
export const dynamic = "force-static";

/** What the phone needs to install Faísca as an app. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Faísca",
    short_name: "Faísca",
    description: "Pesquisa de registos bibliográficos em UNIMARC e de cópias digitais.",
    lang: "pt-PT",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f1f4f9",
    theme_color: "#2341a8",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
