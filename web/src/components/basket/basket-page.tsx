"use client";

import Link from "next/link";
import { useState } from "react";

import { BASKET_EXPORT_URL, useBasket, useClearBasket, useRemoveFromBasket } from "@/lib/api/queries";
import { countLabel, formatLabels } from "@/lib/labels";

/** The records waiting to be exported, the download, and how to import the file. */
export function BasketPage() {
  const basket = useBasket();
  const removeFromBasket = useRemoveFromBasket();
  const clearBasket = useClearBasket();
  const [isConfirmingClear, setIsConfirmingClear] = useState(false);

  if (basket.isPending) return <p role="status">A abrir o cesto…</p>;
  if (basket.isError) return <p role="alert" className="text-failed">{basket.error.message}</p>;

  const { items, count } = basket.data;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-title font-bold leading-tight">Cesto de exportação</h1>
        <p className="max-w-prose text-muted">
          Junte aqui registos de várias pesquisas e descarregue-os num só ficheiro UNIMARC para importar no BIBLIO.NET.
          O Faísca nunca escreve no BIBLIO.NET: a importação é sempre feita por si.
        </p>
      </header>

      {count === 0 ? (
        <p className="max-w-prose">
          O cesto está vazio. Nos resultados de uma{" "}
          <Link href="/" className="font-semibold text-cobalt">
            pesquisa nos catálogos
          </Link>
          , use «Adicionar ao cesto» em cada registo que quiser importar.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-4">
            <a href={BASKET_EXPORT_URL} className="rounded-md bg-cobalt px-5 py-2 font-bold text-surface hover:opacity-90">
              Descarregar {countLabel(count, "registo", "registos")} (ISO 2709)
            </a>
            {isConfirmingClear ? (
              <span className="flex items-center gap-3">
                <span>Retirar todos os registos?</span>
                <button
                  type="button"
                  onClick={() => clearBasket.mutate(undefined, { onSettled: () => setIsConfirmingClear(false) })}
                  className="font-semibold text-failed"
                >
                  Esvaziar o cesto
                </button>
                <button type="button" onClick={() => setIsConfirmingClear(false)} className="font-semibold text-muted">
                  Manter
                </button>
              </span>
            ) : (
              <button type="button" onClick={() => setIsConfirmingClear(true)} className="font-semibold text-muted hover:text-ink">
                Esvaziar o cesto
              </button>
            )}
          </div>

          <ol className="flex flex-col divide-y divide-rule rounded-lg border border-rule bg-surface">
            {items.map((item) => (
              <li key={item.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-3">
                <div className="flex min-w-0 flex-1 flex-col">
                  <Link href={`/registo/?id=${encodeURIComponent(item.record_id)}`} className="font-semibold hover:text-cobalt">
                    {item.title}
                  </Link>
                  <span className="text-small text-muted">
                    {[item.authors[0], item.year, item.target_name].filter(Boolean).join(", ")}
                    {item.source_format === "marc21" ? `, convertido de ${formatLabels.marc21}` : ""}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => removeFromBasket.mutate(item.id)}
                  className="text-small font-semibold text-muted hover:text-failed"
                >
                  Retirar
                </button>
              </li>
            ))}
          </ol>
        </>
      )}

      <section aria-labelledby="encoding-heading" className="max-w-prose rounded-lg border border-rule bg-surface px-4 py-4">
        <h2 id="encoding-heading" className="mb-2 font-bold">
          Sobre o ficheiro
        </h2>
        <p>
          O ficheiro está em UNIMARC, formato ISO 2709, codificado em UTF-8 (o campo 100 $a, posições 26 a 29, indica
          «50», Unicode). Na importação do BIBLIO.NET escolha UNIMARC e UTF-8.
        </p>
        <p className="mt-2 text-muted">
          Se a sua versão do BIBLIO.NET só aceitar ISO 5426 ou ISO 8859-1, os acentos aparecem trocados: converta o ficheiro
          antes de importar (por exemplo, com o MarcEdit) ou peça ao suporte do BIBLIO.NET a importação em UTF-8.
        </p>
      </section>
    </div>
  );
}
