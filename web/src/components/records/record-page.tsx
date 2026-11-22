"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { recordFileUrl, useRecord } from "@/lib/api/queries";

import { AddToBasketButton } from "./add-to-basket-button";
import { MarcRecord } from "./marc-record";
import { SourceBadge } from "./source-badge";

type View = "unimarc" | "original" | "both";

/** One record: its description, the UNIMARC record, and the MARC21 it came from. */
export function RecordPage() {
  const recordId = useSearchParams().get("id");
  const record = useRecord(recordId);
  const [view, setView] = useState<View>("unimarc");

  if (!recordId) return <Missing text="Falta indicar o registo." />;
  if (record.isPending) return <p role="status">A abrir o registo…</p>;
  if (record.isError) return <Missing text={record.error.message} />;

  const { summary, unimarc, original } = record.data;
  const { description } = summary;
  const imprint = [description.edition, description.place_of_publication, description.publisher, description.year]
    .filter(Boolean)
    .join(", ");

  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <BackToResults />
        <h1 className="text-title font-bold leading-tight">{description.title}</h1>
        {description.responsibility ? <p className="text-lead">{description.responsibility}</p> : null}
        {imprint ? <p className="text-muted">{imprint}</p> : null}
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <SourceBadge record={summary} asLink={false} />
          <AddToBasketButton recordId={summary.id} />
          <a href={recordFileUrl(summary.id, "unimarc")} className="font-semibold text-cobalt">
            Descarregar em UNIMARC
          </a>
          {original ? (
            <a href={recordFileUrl(summary.id, "original")} className="font-semibold text-cobalt">
              Descarregar o MARC21 original
            </a>
          ) : null}
        </div>
      </header>

      {original ? (
        <>
          <p className="max-w-prose rounded-md border-l-4 border-slow bg-surface px-4 py-2">
            Este registo veio em MARC21 de {summary.target_name} e foi convertido para UNIMARC. Reveja os dados codificados
            (100, 101, 105) e os pontos de acesso antes de o importar.
          </p>
          <div role="tablist" aria-label="Formato do registo" className="flex gap-1 border-b border-rule">
            {(
              [
                ["unimarc", "UNIMARC"],
                ["original", "MARC21 original"],
                ["both", "Lado a lado"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={view === id}
                onClick={() => setView(id)}
                className={`-mb-px border-b-[3px] px-3 pb-2 pt-1 font-semibold ${
                  view === id ? "border-cobalt text-cobalt" : "border-transparent text-muted hover:text-ink"
                } ${id === "both" ? "hidden lg:block" : ""}`}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      ) : null}

      <div className={view === "both" && original ? "grid gap-6 lg:grid-cols-2" : ""}>
        {view !== "original" || !original ? (
          <RecordPanel title={view === "both" ? "UNIMARC" : null}>
            <MarcRecord record={unimarc} label="Registo em UNIMARC" />
          </RecordPanel>
        ) : null}
        {original && view !== "unimarc" ? (
          <RecordPanel title={view === "both" ? "MARC21 original" : null}>
            <MarcRecord record={original} label="Registo original em MARC21" />
          </RecordPanel>
        ) : null}
      </div>
    </article>
  );
}

function RecordPanel({ title, children }: { title: string | null; children: React.ReactNode }) {
  return (
    <section className="overflow-x-auto rounded-lg border border-rule bg-surface px-4 py-4 sm:px-6">
      {title ? <h2 className="mb-3 font-bold">{title}</h2> : null}
      {children}
    </section>
  );
}

function BackToResults() {
  return (
    <button type="button" onClick={() => history.back()} className="self-start text-small font-semibold text-cobalt">
      Voltar aos resultados
    </button>
  );
}

function Missing({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-3">
      <p role="alert" className="text-failed">
        {text}
      </p>
      <Link href="/" className="font-semibold text-cobalt">
        Fazer uma nova pesquisa
      </Link>
    </div>
  );
}
