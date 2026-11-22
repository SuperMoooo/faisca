"use client";

import { useRouter, useSearchParams } from "next/navigation";

import type { SearchTerms } from "@/lib/api/queries";
import { readSearch, searchQueryString, type SearchTab } from "@/lib/search-params";

import { CatalogueResults } from "./catalogue-results";
import { DigitalResults } from "./digital-results";
import { SearchForm } from "./search-form";
import { SearchTabs } from "./search-tabs";

/** The form, the two tabs and the results of whichever tab is open. */
export function SearchPage() {
  const router = useRouter();
  const { tab, terms } = readSearch(new URLSearchParams(useSearchParams().toString()));
  const hasSearch = Boolean(terms.title || terms.author || terms.isbn);

  function showSearch(nextTab: SearchTab, nextTerms: SearchTerms) {
    router.push(`/?${searchQueryString(nextTab, nextTerms)}`);
  }

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="search-heading" className="flex flex-col gap-4">
        <h1 id="search-heading" className="text-title font-bold leading-tight">
          {tab === "catalogos" ? "Procurar registos nos catálogos" : "Procurar cópias digitais"}
        </h1>
        <SearchTabs current={tab} onChange={(nextTab) => showSearch(nextTab, terms)} />
        {/* key: a new search in the URL (back button) resets the fields to it. */}
        <SearchForm key={searchQueryString(tab, terms)} initialTerms={terms} onSearch={(next) => showSearch(tab, next)} />
      </section>

      {hasSearch ? (
        tab === "catalogos" ? (
          <CatalogueResults terms={terms} />
        ) : (
          <DigitalResults terms={terms} />
        )
      ) : (
        <SearchHelp tab={tab} />
      )}
    </div>
  );
}

function SearchHelp({ tab }: { tab: SearchTab }) {
  return (
    <p className="max-w-prose text-muted">
      {tab === "catalogos"
        ? "Escreva o título, o autor ou o ISBN. A PORBASE, a BNP e os outros catálogos são pesquisados ao mesmo tempo; os registos MARC21 chegam já convertidos para UNIMARC."
        : "Escreva o título, o autor ou o ISBN para saber se o livro já existe em formato digital: Biblioteca Nacional Digital, Europeana, Internet Archive, Open Library e outras."}
    </p>
  );
}
