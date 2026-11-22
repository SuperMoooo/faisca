import Link from "next/link";

import type { RecordSummary } from "@/lib/api/client";
import { formatLabels } from "@/lib/labels";

/**
 * Where a record came from, and in which format. MARC21 records are marked,
 * because what she imports is their conversion, worth a second look.
 */
export function SourceBadge({ record, asLink = true }: { record: RecordSummary; asLink?: boolean }) {
  const isConverted = record.source_format === "marc21";
  const content = (
    <>
      <span className="font-semibold">{shortTargetName(record.target_name)}</span>
      <span className={isConverted ? "text-slow" : "text-muted"}>
        {isConverted ? `${formatLabels.marc21}, convertido` : formatLabels.unimarc}
      </span>
    </>
  );
  const className =
    "inline-flex items-baseline gap-1.5 rounded-md border border-rule bg-paper px-2 py-0.5 text-small";
  if (!asLink) return <span className={className}>{content}</span>;
  return (
    <Link href={`/registo/?id=${encodeURIComponent(record.id)}`} className={`${className} hover:border-cobalt`}>
      {content}
    </Link>
  );
}

/** "PORBASE — Base Nacional…" → "PORBASE": the part before the dash, for badges. */
export function shortTargetName(name: string): string {
  return name.split(" — ")[0];
}
