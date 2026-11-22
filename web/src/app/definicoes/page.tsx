import type { Metadata } from "next";

import { SettingsPage } from "@/components/settings/settings-page";

export const metadata: Metadata = { title: "Definições" };

/** The configured catalogues and digital sources, and whether each answers now. */
export default function Definicoes() {
  return <SettingsPage />;
}
