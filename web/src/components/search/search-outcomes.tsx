"use client";

import { useState } from "react";

/** One target's (or source's) part of a search, as both result lists show it. */
export type Outcome = {
  id: string;
  name: string;
  tone: "ok" | "failed" | "slow" | "muted";
  statusLabel: string;
  detail: string | null;
  error: string | null;
};

const TONE_CLASSES: Record<Outcome["tone"], string> = {
  ok: "bg-ok",
  failed: "bg-failed",
  slow: "bg-slow",
  muted: "bg-muted",
};

/**
 * Which targets answered. Partial results are normal (a catalogue is down,
 * another is slow), so the summary line says it plainly and the list explains each.
 */
export function SearchOutcomes({ outcomes, noun }: { outcomes: Outcome[]; noun: [string, string] }) {
  const [isOpen, setIsOpen] = useState(false);
  const answered = outcomes.filter((outcome) => outcome.tone === "ok").length;
  const problems = outcomes.filter((outcome) => outcome.tone === "failed" || outcome.tone === "slow");

  return (
    <section aria-label="Estado da pesquisa" className="rounded-lg border border-rule bg-surface">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-left"
      >
        <span className="flex gap-1" aria-hidden="true">
          {outcomes.map((outcome) => (
            <span key={outcome.id} className={`h-2.5 w-2.5 rounded-full ${TONE_CLASSES[outcome.tone]}`} />
          ))}
        </span>
        <span>
          {answered} de {outcomes.length} {outcomes.length === 1 ? noun[0] : noun[1]} responderam
          {problems.length > 0 ? (
            <span className="text-muted">, {problems.map((outcome) => outcome.name).join(", ")} não</span>
          ) : null}
        </span>
        <span className="ml-auto text-small font-semibold text-cobalt">{isOpen ? "Esconder detalhes" : "Ver detalhes"}</span>
      </button>
      {isOpen ? (
        <ul className="divide-y divide-rule border-t border-rule">
          {outcomes.map((outcome) => (
            <li key={outcome.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2">
              <span className={`h-2.5 w-2.5 shrink-0 self-center rounded-full ${TONE_CLASSES[outcome.tone]}`} aria-hidden="true" />
              <span className="font-semibold">{outcome.name}</span>
              <span className="text-muted">{outcome.statusLabel}</span>
              {outcome.detail ? <span className="text-small text-muted">{outcome.detail}</span> : null}
              {outcome.error ? <span className="basis-full pl-5 text-small text-failed">{outcome.error}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

/** "1,2 s", "850 ms": how long a target took, in Portuguese number format. */
export function formatElapsed(milliseconds: number | null | undefined): string | null {
  if (milliseconds == null) return null;
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toLocaleString("pt-PT", { maximumFractionDigits: 1 })} s`;
}
