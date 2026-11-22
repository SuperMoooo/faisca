import type { Metadata } from "next";
import { Suspense } from "react";

import { ComparePage } from "@/components/records/compare-page";

export const metadata: Metadata = { title: "Comparar registos" };

/** /comparar/?ids=a,b,c: two or three records of a book, field by field. */
export default function Comparar() {
  return (
    <Suspense fallback={null}>
      <ComparePage />
    </Suspense>
  );
}
