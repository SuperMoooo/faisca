import type { Metadata } from "next";
import { Suspense } from "react";

import { RecordPage } from "@/components/records/record-page";

export const metadata: Metadata = { title: "Registo" };

/** /registo/?id=…: one record in UNIMARC, with its MARC21 original when converted. */
export default function Registo() {
  return (
    <Suspense fallback={null}>
      <RecordPage />
    </Suspense>
  );
}
