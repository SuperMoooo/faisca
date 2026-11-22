import type { SearchTerms } from "./api/queries";

/** Which kind of search the results show. */
export type SearchTab = "catalogos" | "digitais";

const TERM_KEYS = ["title", "author", "isbn", "year"] as const;

/**
 * The search lives in the URL (/?tab=catalogos&title=…), so the back button,
 * a bookmark and a reload all return to the same results.
 */
export function readSearch(params: URLSearchParams): { tab: SearchTab; terms: SearchTerms } {
  const terms: SearchTerms = {};
  for (const key of TERM_KEYS) {
    const value = params.get(key)?.trim();
    if (value) terms[key] = value;
  }
  const tab: SearchTab = params.get("tab") === "digitais" ? "digitais" : "catalogos";
  return { tab, terms };
}

/** The query string for a search, without empty fields. */
export function searchQueryString(tab: SearchTab, terms: SearchTerms): string {
  const params = new URLSearchParams({ tab });
  for (const key of TERM_KEYS) {
    const value = terms[key]?.trim();
    if (value) params.set(key, value);
  }
  return params.toString();
}
