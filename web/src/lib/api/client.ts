import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

/**
 * The typed client for /api/v1. Paths and shapes come from schema.d.ts,
 * generated from contracts/openapi.json (`npm run generate:api`), so a
 * backend change that breaks the web app fails `npm run typecheck`.
 *
 * Same origin: FastAPI serves this app in production, and `next dev` proxies /api.
 */
export const api = createClient<paths>({ baseUrl: "" });

type Schemas = components["schemas"];

export type SearchQuery = Schemas["SearchQuery"];
export type CatalogueSearchResponse = Schemas["CatalogueSearchResponse"];
export type RecordGroup = Schemas["RecordGroup"];
export type RecordSummary = Schemas["RecordSummary"];
export type RecordDetail = Schemas["RecordDetail"];
export type MarcRecordView = Schemas["MarcRecordView"];
export type MarcFieldView = Schemas["MarcFieldView"];
export type TargetOutcome = Schemas["TargetOutcome"];
export type DigitalSearchResponse = Schemas["DigitalSearchResponse"];
export type DigitalCopy = Schemas["DigitalCopy"];
export type SourceOutcome = Schemas["SourceOutcome"];
export type BasketRead = Schemas["BasketRead"];
export type BasketItemRead = Schemas["BasketItemRead"];
export type TargetList = Schemas["TargetList"];
export type TargetRead = Schemas["TargetRead"];
export type TargetStatus = Schemas["TargetStatus"];

/** The error the API sends for every refusal: `{"error": {"code", "message"}}`. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/** Turns an API error body (ours, or FastAPI's 422 list) into one sentence to show. */
export function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const shaped = body as { error?: { message?: string }; detail?: { msg?: string }[] | string };
    if (shaped.error?.message) return shaped.error.message;
    if (Array.isArray(shaped.detail) && shaped.detail[0]?.msg) {
      // Pydantic prefixes our validator messages with "Value error, ".
      return shaped.detail[0].msg.replace(/^Value error, /, "");
    }
    if (typeof shaped.detail === "string") return shaped.detail;
  }
  return `O servidor respondeu com o erro ${status}.`;
}

/** Unwraps an openapi-fetch result: the data, or an ApiError with the API's message. */
export function unwrap<Data>(result: { data?: Data; error?: unknown; response: Response }): Data {
  if (result.data === undefined) {
    throw new ApiError(errorMessage(result.error, result.response.status), result.response.status);
  }
  return result.data;
}
