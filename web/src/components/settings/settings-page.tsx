"use client";

import { useState } from "react";

import type { TargetRead, TargetStatus } from "@/lib/api/client";
import { useTargets, useTargetStatus } from "@/lib/api/queries";
import { formatLabels, reachabilityLabels } from "@/lib/labels";

import { formatElapsed } from "../search/search-outcomes";

// Catalogue protocols by their usual names; digital sources are web APIs and need no label.
const PROTOCOL_LABELS: Record<string, string | undefined> = { z3950: "Z39.50", sru: "SRU" };

const REACHABILITY_TONES: Record<TargetStatus["reachability"], string> = {
  reachable: "bg-ok",
  blocked: "bg-slow",
  unreachable: "bg-failed",
  disabled: "bg-muted",
};

/** Lists targets from config/targets.yaml and, on request, checks which answer right now. */
export function SettingsPage() {
  const targets = useTargets();
  const [isChecking, setIsChecking] = useState(false);
  const status = useTargetStatus(isChecking);

  if (targets.isPending) return <p role="status">A carregar os catálogos…</p>;
  if (targets.isError) return <p role="alert" className="text-failed">{targets.error.message}</p>;

  const statusById = new Map((status.data?.statuses ?? []).map((entry) => [entry.id, entry]));

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-title font-bold leading-tight">Definições</h1>
        <p className="max-w-prose text-muted">
          Os catálogos e as fontes de cópias digitais vêm do ficheiro config/targets.yaml. Para acrescentar um, veja o README.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={status.isFetching}
            onClick={() => (isChecking ? status.refetch() : setIsChecking(true))}
            className="rounded-md border border-cobalt px-4 py-1.5 font-semibold text-cobalt hover:bg-cobalt-soft disabled:opacity-60"
          >
            {status.isFetching ? "A verificar…" : status.data ? "Verificar de novo" : "Verificar se respondem"}
          </button>
          {status.isError ? <span role="alert" className="text-failed">{status.error.message}</span> : null}
        </div>
      </header>

      <TargetTable heading="Catálogos" targets={targets.data.catalogues} statusById={statusById} />
      <TargetTable heading="Cópias digitais" targets={targets.data.digital_sources} statusById={statusById} />
    </div>
  );
}

function TargetTable({
  heading,
  targets,
  statusById,
}: {
  heading: string;
  targets: TargetRead[];
  statusById: Map<string, TargetStatus>;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-heading font-bold">{heading}</h2>
      <ul className="flex flex-col divide-y divide-rule rounded-lg border border-rule bg-surface">
        {targets.map((target) => {
          const status = statusById.get(target.id);
          return (
            <li key={target.id} className="flex flex-col gap-1 px-4 py-3">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-semibold">{target.name}</span>
                <span className="text-small text-muted">
                  {[target.country, PROTOCOL_LABELS[target.protocol], target.format ? formatLabels[target.format] : null]
                    .filter(Boolean)
                    .join(", ")}
                </span>
                {!target.enabled ? <span className="text-small font-semibold text-muted">Desativado</span> : null}
                {status ? (
                  <span className="ml-auto inline-flex items-center gap-2 text-small">
                    <span className={`h-2.5 w-2.5 rounded-full ${REACHABILITY_TONES[status.reachability]}`} aria-hidden="true" />
                    {reachabilityLabels[status.reachability]}
                    {status.latency_ms != null ? <span className="text-muted">{formatElapsed(status.latency_ms)}</span> : null}
                    {status.detail ? <span className="text-muted">{status.detail}</span> : null}
                  </span>
                ) : null}
              </div>
              <span className="break-all font-mono text-small text-muted">{target.endpoint}</span>
              {target.notes ? <p className="max-w-prose text-small text-muted">{target.notes}</p> : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
