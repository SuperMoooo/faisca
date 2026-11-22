/**
 * Every Portuguese (pt-PT) word the interface uses for an API value, in one
 * place, so a status is called the same thing on every screen.
 */

import type { DigitalCopy, SourceOutcome, TargetOutcome, TargetStatus } from "./api/client";

export const targetSearchStatusLabels: Record<TargetOutcome["status"], string> = {
  ok: "Respondeu",
  failed: "Falhou",
  timed_out: "Sem resposta a tempo",
  unavailable: "Indisponível neste servidor",
};

export const sourceSearchStatusLabels: Record<SourceOutcome["status"], string> = {
  ok: "Respondeu",
  failed: "Falhou",
  timed_out: "Sem resposta a tempo",
  skipped: "Não pesquisado",
};

export const accessLabels: Record<DigitalCopy["access"], string> = {
  free: "Acesso livre",
  restricted: "Acesso restrito",
  unknown: "Acesso por confirmar",
};

export const reachabilityLabels: Record<TargetStatus["reachability"], string> = {
  reachable: "Acessível",
  blocked: "Bloqueia o acesso",
  unreachable: "Inacessível",
  disabled: "Desativado",
};

export const formatLabels = {
  unimarc: "UNIMARC",
  marc21: "MARC21",
} as const;

/** "1 registo", "3 registos": Portuguese plural for counts the interface shows. */
export function countLabel(count: number, singular: string, plural: string): string {
  return `${count.toLocaleString("pt-PT")} ${count === 1 ? singular : plural}`;
}
