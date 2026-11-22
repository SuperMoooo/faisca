"use client";

import { useAddToBasket, useBasket } from "@/lib/api/queries";

/** Adds one record to the export basket; says so once it is there. */
export function AddToBasketButton({ recordId, compact = false }: { recordId: string; compact?: boolean }) {
  const { data: basket } = useBasket();
  const addToBasket = useAddToBasket();
  const isInBasket = basket?.items.some((item) => item.record_id === recordId) ?? false;

  if (isInBasket) {
    return <span className="px-1 text-small font-semibold text-ok">No cesto</span>;
  }
  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        disabled={addToBasket.isPending}
        onClick={() => addToBasket.mutate(recordId)}
        className={`rounded-md border border-cobalt font-semibold text-cobalt transition-colors hover:bg-cobalt-soft disabled:opacity-60 ${
          compact ? "px-2 py-0.5 text-small" : "px-3 py-1.5"
        }`}
      >
        {addToBasket.isPending ? "A adicionar…" : "Adicionar ao cesto"}
      </button>
      {addToBasket.isError ? (
        <span role="alert" className="text-small text-failed">
          {addToBasket.error.message}
        </span>
      ) : null}
    </span>
  );
}
