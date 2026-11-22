"use client";

import Link from "next/link";
import { useState } from "react";

import type { RecordGroup, RecordSummary, TargetOutcome } from "@/lib/api/client";
import { useCatalogueSearch, type SearchTerms } from "@/lib/api/queries";
import { countLabel, targetSearchStatusLabels } from "@/lib/labels";

import { AddToBasketButton } from "../records/add-to-basket-button";
import { SourceBadge } from "../records/source-badge";
import { formatElapsed, SearchOutcomes, type Outcome } from "./search-outcomes";
import { SearchingNotice } from "./searching-notice";

// The compare view puts records side by side; more than three no longer fit.
const MAX_COMPARED = 3;

/** The catalogue search: per-target status, then one row per book with every source found. */
export function CatalogueResults({ terms }: { terms: SearchTerms }) {
  const search = useCatalogueSearch(terms);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  if (search.isPending) return <SearchingNotice text="A pesquisar os catálogos…" />;
  if (search.isError) {
    return (
      <p role="alert" className="rounded-lg border border-failed bg-surface px-4 py-3 text-failed">
        {search.error.message}
      </p>
    );
  }

  const { groups, targets, record_count: recordCount } = search.data;

  function toggleSelected(recordId: string) {
    setSelectedIds((current) =>
      current.includes(recordId)
        ? current.filter((id) => id !== recordId)
        : [...current, recordId].slice(-MAX_COMPARED),
    );
  }

  return (
    <section aria-labelledby="results-heading" className="flex flex-col gap-4">
      <SearchOutcomes outcomes={targets.map(catalogueOutcome)} noun={["catálogo", "catálogos"]} />
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 id="results-heading" className="text-heading font-bold">
          {countLabel(groups.length, "livro", "livros")}
        </h2>
        <p className="text-muted">{countLabel(recordCount, "registo encontrado", "registos encontrados")}</p>
      </div>
      {groups.length === 0 ? (
        <p className="max-w-prose text-muted">
          Nenhum catálogo encontrou registos. Experimente só o apelido do autor, menos palavras do título, ou o ISBN.
        </p>
      ) : (
        <ol className="flex flex-col divide-y divide-rule rounded-lg border border-rule bg-surface">
          {groups.map((group) => (
            <BookRow key={group.records[0].id} group={group} selectedIds={selectedIds} onToggle={toggleSelected} />
          ))}
        </ol>
      )}
      {selectedIds.length > 0 ? <CompareBar selectedIds={selectedIds} onClear={() => setSelectedIds([])} /> : null}
    </section>
  );
}

function catalogueOutcome(outcome: TargetOutcome): Outcome {
  const tone = outcome.status === "ok" ? "ok" : outcome.status === "timed_out" ? "slow" : outcome.status === "unavailable" ? "muted" : "failed";
  const details = [
    outcome.hit_count != null ? countLabel(outcome.hit_count, "registo", "registos") : null,
    outcome.from_cache ? "da cache" : formatElapsed(outcome.elapsed_ms),
  ].filter(Boolean);
  return {
    id: outcome.target_id,
    name: outcome.target_name,
    tone,
    statusLabel: targetSearchStatusLabels[outcome.status],
    detail: details.length ? details.join(", ") : null,
    error: outcome.error ?? null,
  };
}

/** One book: the first (preferred) record's description, and every source that has it. */
function BookRow({
  group,
  selectedIds,
  onToggle,
}: {
  group: RecordGroup;
  selectedIds: string[];
  onToggle: (recordId: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [first] = group.records;
  const description = first.description;
  const imprint = [description.edition, description.place_of_publication, description.publisher, description.year]
    .filter(Boolean)
    .join(", ");
  const otherCount = group.records.length - 1;

  return (
    <li className="flex flex-col gap-2 px-4 py-4">
      <div className="flex flex-col gap-1">
        <Link href={`/registo/?id=${encodeURIComponent(first.id)}`} className="text-lead font-semibold leading-snug hover:text-cobalt">
          {description.title}
          {description.other_title_information ? (
            <span className="font-normal text-muted"> : {description.other_title_information}</span>
          ) : null}
        </Link>
        {description.responsibility || description.authors.length ? (
          <p>{description.responsibility ?? description.authors.join("; ")}</p>
        ) : null}
        {imprint ? <p className="text-muted">{imprint}</p> : null}
        {description.isbns.length ? <p className="text-small text-muted">ISBN {description.isbns.join(", ")}</p> : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {group.records.map((record) => (
          <SourceBadge key={record.id} record={record} />
        ))}
        {first.has_digital_copy ? <span className="text-small font-semibold text-ok">Tem cópia digital</span> : null}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <AddToBasketButton recordId={first.id} compact />
        {otherCount > 0 ? (
          <button
            type="button"
            aria-expanded={isExpanded}
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-small font-semibold text-cobalt"
          >
            {isExpanded ? "Esconder os registos" : `Escolher entre ${group.records.length} registos`}
          </button>
        ) : (
          <SelectForCompare record={first} selectedIds={selectedIds} onToggle={onToggle} />
        )}
      </div>

      {isExpanded ? (
        <ul className="mt-1 flex flex-col divide-y divide-rule rounded-md border border-rule">
          {group.records.map((record) => (
            <GroupRecord key={record.id} record={record} selectedIds={selectedIds} onToggle={onToggle} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/** One source's record inside an expanded book: what differs, and what can be done with it. */
function GroupRecord({
  record,
  selectedIds,
  onToggle,
}: {
  record: RecordSummary;
  selectedIds: string[];
  onToggle: (recordId: string) => void;
}) {
  const { description } = record;
  const differences = [description.edition, description.publisher, description.year, description.physical_description]
    .filter(Boolean)
    .join(", ");
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2">
      <SourceBadge record={record} />
      <span className="min-w-0 flex-1 text-small text-muted">{differences}</span>
      <SelectForCompare record={record} selectedIds={selectedIds} onToggle={onToggle} />
      <AddToBasketButton recordId={record.id} compact />
    </li>
  );
}

function SelectForCompare({
  record,
  selectedIds,
  onToggle,
}: {
  record: RecordSummary;
  selectedIds: string[];
  onToggle: (recordId: string) => void;
}) {
  return (
    <label className="inline-flex items-center gap-1.5 text-small">
      <input
        type="checkbox"
        checked={selectedIds.includes(record.id)}
        onChange={() => onToggle(record.id)}
        className="h-4 w-4 accent-[var(--cobalt)]"
      />
      Comparar
    </label>
  );
}

/** Appears once records are ticked: opens them side by side. */
function CompareBar({ selectedIds, onClear }: { selectedIds: string[]; onClear: () => void }) {
  const canCompare = selectedIds.length >= 2;
  return (
    <div className="sticky bottom-4 z-10 flex flex-wrap items-center gap-3 rounded-lg border border-cobalt bg-surface px-4 py-3 shadow-lg">
      <span>
        {countLabel(selectedIds.length, "registo escolhido", "registos escolhidos")}
        {canCompare ? null : <span className="text-muted">, escolha mais um para comparar</span>}
      </span>
      <span className="ml-auto flex gap-3">
        <button type="button" onClick={onClear} className="font-semibold text-muted hover:text-ink">
          Limpar
        </button>
        {canCompare ? (
          <Link
            href={`/comparar/?ids=${selectedIds.map(encodeURIComponent).join(",")}`}
            className="rounded-md bg-cobalt px-4 py-1.5 font-bold text-surface"
          >
            Comparar lado a lado
          </Link>
        ) : null}
      </span>
    </div>
  );
}
