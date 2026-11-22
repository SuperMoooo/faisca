"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type SearchQuery } from "./client";

/** A search form value, without the target filter (the forms do not choose targets). */
export type SearchTerms = Pick<SearchQuery, "title" | "author" | "isbn" | "year">;

// Searches are live and can take tens of seconds; the backend caches them for
// a day, so the browser keeps its copy for the session instead of refetching
// every time a tab regains focus.
const SEARCH_STALE_TIME_MS = 30 * 60 * 1000;

function hasTerms(terms: SearchTerms): boolean {
  return Boolean(terms.title || terms.author || terms.isbn);
}

/** Federated catalogue search. Runs only when the form has a title, author or ISBN. */
export function useCatalogueSearch(terms: SearchTerms) {
  return useQuery({
    queryKey: ["catalogue-search", terms],
    queryFn: async () => unwrap(await api.GET("/api/v1/catalogues/search", { params: { query: terms } })),
    enabled: hasTerms(terms),
    staleTime: SEARCH_STALE_TIME_MS,
    retry: false,
  });
}

/** Digital-copy search across BND, Europeana, Internet Archive… */
export function useDigitalSearch(terms: SearchTerms) {
  return useQuery({
    queryKey: ["digital-search", terms],
    queryFn: async () => unwrap(await api.GET("/api/v1/digital/search", { params: { query: terms } })),
    enabled: hasTerms(terms),
    staleTime: SEARCH_STALE_TIME_MS,
    retry: false,
  });
}

/** One record in UNIMARC, with the MARC21 original when it was converted. */
export function useRecord(recordId: string | null) {
  return useQuery({
    queryKey: ["record", recordId],
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/records/{record_id}", { params: { path: { record_id: recordId ?? "" } } })),
    enabled: Boolean(recordId),
    staleTime: Infinity,
    retry: false,
  });
}

/** The export basket. */
export function useBasket() {
  return useQuery({
    queryKey: ["basket"],
    queryFn: async () => unwrap(await api.GET("/api/v1/basket")),
  });
}

/** Adds a record to the basket; the header count and basket page update. */
export function useAddToBasket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (recordId: string) =>
      unwrap(await api.POST("/api/v1/basket", { body: { record_id: recordId } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["basket"] }),
  });
}

/** Takes one record out of the basket. */
export function useRemoveFromBasket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: number) => {
      const result = await api.DELETE("/api/v1/basket/{item_id}", { params: { path: { item_id: itemId } } });
      if (!result.response.ok) unwrap(result);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["basket"] }),
  });
}

/** Empties the basket. */
export function useClearBasket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const result = await api.DELETE("/api/v1/basket");
      if (!result.response.ok) unwrap(result);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["basket"] }),
  });
}

/** Every configured target. */
export function useTargets() {
  return useQuery({
    queryKey: ["targets"],
    queryFn: async () => unwrap(await api.GET("/api/v1/targets")),
    staleTime: Infinity,
  });
}

/** Contacts every target now; only when the settings page asks. */
export function useTargetStatus(enabled: boolean) {
  return useQuery({
    queryKey: ["target-status"],
    queryFn: async () => unwrap(await api.GET("/api/v1/targets/status")),
    enabled,
    staleTime: 60 * 1000,
  });
}

/** Where the browser downloads the basket as one ISO 2709 file. */
export const BASKET_EXPORT_URL = "/api/v1/basket/export";

/** Where the browser downloads one record as ISO 2709. */
export function recordFileUrl(recordId: string, variant: "unimarc" | "original"): string {
  return `/api/v1/records/${encodeURIComponent(recordId)}/iso2709?variant=${variant}`;
}
