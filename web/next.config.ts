import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

// The FastAPI backend during `npm run dev` (see backend/README or the root README).
const DEV_API_ORIGIN = process.env.FAISCA_API_ORIGIN ?? "http://127.0.0.1:8000";

/**
 * Two shapes of one app:
 * - `next build` makes a static export (web/out) that FastAPI serves at "/",
 *   so the browser talks to /api/v1 on the same origin, with no Node server.
 * - `next dev` proxies /api and /health to FastAPI. Rewrites are not allowed
 *   together with `output: "export"`, which is why the config depends on the phase.
 */
export default function nextConfig(phase: string): NextConfig {
  const shared: NextConfig = {
    // /cesto → cesto/index.html, which FastAPI's StaticFiles serves as a directory.
    trailingSlash: true,
    turbopack: {
      rules: {
        "*.css": {
          loaders: ["@tailwindcss/turbopack"],
          as: "*.css",
        },
      },
    },
  };

  if (phase === PHASE_DEVELOPMENT_SERVER) {
    return {
      ...shared,
      async rewrites() {
        return [
          { source: "/api/:path*", destination: `${DEV_API_ORIGIN}/api/:path*` },
          { source: "/health", destination: `${DEV_API_ORIGIN}/health` },
        ];
      },
    };
  }

  return { ...shared, output: "export", images: { unoptimized: true } };
}
