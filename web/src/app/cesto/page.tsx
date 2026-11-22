import type { Metadata } from "next";

import { BasketPage } from "@/components/basket/basket-page";

export const metadata: Metadata = { title: "Cesto de exportação" };

/** The export basket: records chosen across searches, downloaded as one ISO 2709 file. */
export default function Cesto() {
  return <BasketPage />;
}
