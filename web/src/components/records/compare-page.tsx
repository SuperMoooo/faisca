"use client";

import { useQueries } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { api, unwrap, type MarcFieldView, type RecordDetail } from "@/lib/api/client";

import { AddToBasketButton } from "./add-to-basket-button";
import { fieldText, MarcField } from "./marc-record";
import { SourceBadge } from "./source-badge";

const MAX_COMPARED = 3;

/** One line of the comparison: the same tag (and occurrence) in each record. */
type CompareRow = { key: string; tag: string; fields: (MarcFieldView | undefined)[] };

/** Two or three UNIMARC records of the same book, aligned by tag; differences light up. */
export function ComparePage() {
  const ids = (useSearchParams().get("ids") ?? "").split(",").filter(Boolean).slice(0, MAX_COMPARED);
  const [isDifferencesOnly, setIsDifferencesOnly] = useState(false);
  const records = useQueries({
    queries: ids.map((recordId) => ({
      queryKey: ["record", recordId],
      queryFn: async () =>
        unwrap(await api.GET("/api/v1/records/{record_id}", { params: { path: { record_id: recordId } } })),
      staleTime: Infinity,
      retry: false,
    })),
  });

  if (ids.length < 2) {
    return (
      <p>
        Escolha dois ou três registos nos resultados para os comparar.{" "}
        <Link href="/" className="font-semibold text-cobalt">
          Ir para a pesquisa
        </Link>
      </p>
    );
  }
  if (records.some((record) => record.isPending)) return <p role="status">A abrir os registos…</p>;
  const failed = records.find((record) => record.isError);
  if (failed?.error) return <p role="alert" className="text-failed">{failed.error.message}</p>;

  const details = records.map((record) => record.data as RecordDetail);
  const rows = alignFields(details);
  const visibleRows = isDifferencesOnly ? rows.filter(isDifferent) : rows;

  return (
    <article className="flex flex-col gap-4">
      <header className="flex flex-col gap-2">
        <button type="button" onClick={() => history.back()} className="self-start text-small font-semibold text-cobalt">
          Voltar aos resultados
        </button>
        <h1 className="text-title font-bold leading-tight">Comparar registos</h1>
        <p className="max-w-prose text-muted">
          Os campos assinalados diferem do primeiro registo. Os registos MARC21 aparecem já convertidos para UNIMARC.
        </p>
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={isDifferencesOnly}
            onChange={(event) => setIsDifferencesOnly(event.target.checked)}
            className="h-4 w-4 accent-[var(--cobalt)]"
          />
          Mostrar só os campos diferentes
        </label>
      </header>

      {/* The table scrolls sideways on a phone; the page itself never does. */}
      <div className="overflow-x-auto rounded-lg border border-rule bg-surface">
        <table className="w-full min-w-[48rem] border-collapse text-left">
          <thead>
            <tr className="border-b border-rule align-top">
              {details.map((detail) => (
                <th key={detail.summary.id} scope="col" className="w-1/3 px-4 py-3 font-normal">
                  <div className="flex flex-col items-start gap-2">
                    <SourceBadge record={detail.summary} />
                    <span className="font-semibold">{detail.summary.description.title}</span>
                    <AddToBasketButton recordId={detail.summary.id} compact />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="marc-record">
            {visibleRows.map((row) => (
              <tr key={row.key} className="border-b border-rule last:border-0 align-top">
                {row.fields.map((field, column) => (
                  <td key={column} className="px-4 py-0.5">
                    {field ? (
                      <MarcField
                        field={field}
                        inTableCell
                        isChanged={column > 0 && fieldText(field) !== fieldText(row.fields[0])}
                      />
                    ) : (
                      <span className="marc-field marc-field-changed text-muted">
                        <span className="marc-tag">{row.tag}</span>
                        <span />
                        <span>não tem</span>
                      </span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

/**
 * Lines up the records' fields: every tag present in any record, in tag
 * order, and for a repeated tag (two 700s) its first, second… occurrence on
 * the same line.
 */
function alignFields(details: RecordDetail[]): CompareRow[] {
  const occurrences = details.map((detail) => groupByTag(detail.unimarc.fields));
  const tags = [...new Set(details.flatMap((detail) => detail.unimarc.fields.map((field) => field.tag)))].sort();
  const rows: CompareRow[] = [];
  for (const tag of tags) {
    const deepest = Math.max(...occurrences.map((byTag) => byTag.get(tag)?.length ?? 0));
    for (let index = 0; index < deepest; index += 1) {
      rows.push({ key: `${tag}-${index}`, tag, fields: occurrences.map((byTag) => byTag.get(tag)?.[index]) });
    }
  }
  return rows;
}

function groupByTag(fields: MarcFieldView[]): Map<string, MarcFieldView[]> {
  const byTag = new Map<string, MarcFieldView[]>();
  for (const field of fields) byTag.set(field.tag, [...(byTag.get(field.tag) ?? []), field]);
  return byTag;
}

function isDifferent(row: CompareRow): boolean {
  const first = fieldText(row.fields[0]);
  return row.fields.some((field) => fieldText(field) !== first);
}
