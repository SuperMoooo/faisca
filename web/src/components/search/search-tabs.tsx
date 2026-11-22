"use client";

import type { SearchTab } from "@/lib/search-params";

const TABS: { id: SearchTab; label: string }[] = [
  { id: "catalogos", label: "Catálogos" },
  { id: "digitais", label: "Cópias digitais" },
];

/** Switches between catalogue records and digital copies, keeping the search terms. */
export function SearchTabs({ current, onChange }: { current: SearchTab; onChange: (tab: SearchTab) => void }) {
  return (
    <div role="tablist" aria-label="Tipo de pesquisa" className="flex gap-1 border-b border-rule">
      {TABS.map((tab) => {
        const isSelected = tab.id === current;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isSelected}
            onClick={() => onChange(tab.id)}
            className={`-mb-px border-b-[3px] px-3 pb-2 pt-1 font-semibold transition-colors ${
              isSelected ? "border-cobalt text-cobalt" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
