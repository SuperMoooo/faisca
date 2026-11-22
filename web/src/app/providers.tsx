"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  // A fresh client per prerender at build time; one shared client in the
  // browser, so searches survive moving between pages.
  if (typeof window === "undefined") return new QueryClient();
  browserQueryClient ??= new QueryClient({
    defaultOptions: { queries: { refetchOnWindowFocus: false } },
  });
  return browserQueryClient;
}

/** Makes the API query cache available to every page. */
export function Providers({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>;
}
