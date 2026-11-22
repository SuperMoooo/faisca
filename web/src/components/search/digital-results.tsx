"use client";

import Link from "next/link";
import { useState } from "react";

import type { DigitalCopy, SourceOutcome } from "@/lib/api/client";
import { useDigitalSearch, type SearchTerms } from "@/lib/api/queries";
import { accessLabels, countLabel, sourceSearchStatusLabels } from "@/lib/labels";

import { formatElapsed, SearchOutcomes, type Outcome } from "./search-outcomes";
import { SearchingNotice } from "./searching-notice";

/** Digital copies from every source, open-access ones easy to pick out. */
export function DigitalResults({ terms }: { terms: SearchTerms }) {
  const search = useDigitalSearch(terms);
  const [isFreeOnly, setIsFreeOnly] = useState(false);

  if (search.isPending) return <SearchingNotice text="A procurar cópias digitais…" />;
  if (search.isError) {
    return (
      <p role="alert" className="rounded-lg border border-failed bg-surface px-4 py-3 text-failed">
        {search.error.message}
      </p>
    );
  }

  const copies = isFreeOnly ? search.data.copies.filter((copy) => copy.access === "free") : search.data.copies;

  return (
    <section aria-labelledby="copies-heading" className="flex flex-col gap-4">
      <SearchOutcomes outcomes={search.data.sources.map(sourceOutcome)} noun={["fonte", "fontes"]} />
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
        <h2 id="copies-heading" className="text-heading font-bold">
          {countLabel(copies.length, "cópia digital", "cópias digitais")}
        </h2>
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={isFreeOnly}
            onChange={(event) => setIsFreeOnly(event.target.checked)}
            className="h-4 w-4 accent-[var(--cobalt)]"
          />
          Só acesso livre
        </label>
      </div>
      {copies.length === 0 ? (
        <p className="max-w-prose text-muted">
          {isFreeOnly
            ? "Nenhuma cópia de acesso livre. Desmarque o filtro para ver as de acesso restrito."
            : "Nenhuma fonte tem uma cópia digital. Experimente outra forma do título ou só o apelido do autor."}
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-rule rounded-lg border border-rule bg-surface">
          {copies.map((copy) => (
            <CopyRow key={`${copy.source_id}:${copy.url}`} copy={copy} />
          ))}
        </ul>
      )}
    </section>
  );
}

function sourceOutcome(outcome: SourceOutcome): Outcome {
  const tone = outcome.status === "ok" ? "ok" : outcome.status === "timed_out" ? "slow" : outcome.status === "skipped" ? "muted" : "failed";
  const detail = outcome.status === "ok"
    ? [countLabel(outcome.found_count, "cópia", "cópias"), outcome.from_cache ? "da cache" : formatElapsed(outcome.elapsed_ms)]
        .filter(Boolean)
        .join(", ")
    : null;
  return {
    id: outcome.source_id,
    name: outcome.source_name,
    tone,
    statusLabel: sourceSearchStatusLabels[outcome.status],
    detail,
    error: outcome.error ?? null,
  };
}

function CopyRow({ copy }: { copy: DigitalCopy }) {
  const isFree = copy.access === "free";
  const meta = [copy.authors.slice(0, 2).join("; "), copy.year, copy.provider].filter(Boolean).join(", ");
  return (
    <li className="flex gap-4 px-4 py-3">
      {copy.thumbnail_url ? (
        // External thumbnails, any size: next/image would need a loader for a static export.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={copy.thumbnail_url} alt="" loading="lazy" className="h-20 w-14 shrink-0 rounded-sm border border-rule bg-paper object-cover" />
      ) : (
        <span className="h-20 w-14 shrink-0 rounded-sm border border-dashed border-rule" aria-hidden="true" />
      )}
      <div className="flex min-w-0 flex-col gap-1">
        <a href={copy.url} target="_blank" rel="noreferrer" className="font-semibold leading-snug hover:text-cobalt">
          {copy.title}
        </a>
        {meta ? <p className="text-small text-muted">{meta}</p> : null}
        <p className="flex flex-wrap items-center gap-2 text-small">
          <span className="font-semibold">{copy.source_name}</span>
          <span
            className={`rounded-sm px-1.5 font-semibold ${isFree ? "bg-spark-soft text-ink" : "text-muted"}`}
          >
            {accessLabels[copy.access]}
          </span>
          {copy.catalogue_record_id ? (
            <Link href={`/registo/?id=${encodeURIComponent(copy.catalogue_record_id)}`} className="font-semibold text-cobalt">
              Ver o registo da BNP
            </Link>
          ) : null}
        </p>
      </div>
    </li>
  );
}
