"use client";

import { useState, type FormEvent } from "react";

import type { SearchTerms } from "@/lib/api/queries";

type FieldName = keyof SearchTerms;

const FIELDS: { name: FieldName; label: string; hint?: string; inputMode?: "numeric"; width: string }[] = [
  { name: "title", label: "Título", width: "sm:col-span-5" },
  { name: "author", label: "Autor", width: "sm:col-span-3" },
  { name: "isbn", label: "ISBN", hint: "Com ou sem hífenes", width: "sm:col-span-2" },
  { name: "year", label: "Ano", inputMode: "numeric", width: "sm:col-span-2" },
];

/** Title, author, ISBN and year. A year alone is not a search: it needs one of the others. */
export function SearchForm({
  initialTerms,
  onSearch,
}: {
  initialTerms: SearchTerms;
  onSearch: (terms: SearchTerms) => void;
}) {
  const [terms, setTerms] = useState<SearchTerms>(initialTerms);
  const [problem, setProblem] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!terms.title?.trim() && !terms.author?.trim() && !terms.isbn?.trim()) {
      setProblem("Escreva pelo menos o título, o autor ou o ISBN.");
      return;
    }
    if (terms.year && !/^\d{4}$/.test(terms.year.trim())) {
      setProblem("O ano tem quatro algarismos, por exemplo 1880.");
      return;
    }
    setProblem(null);
    onSearch(terms);
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-12">
        {FIELDS.map((field) => (
          <label
            key={field.name}
            className={`flex flex-col gap-1 ${field.name === "title" || field.name === "author" ? "col-span-2" : ""} ${field.width}`}
          >
            <span className="font-semibold">
              {field.label}
              {field.hint ? <span className="ml-2 text-small font-normal text-muted">{field.hint}</span> : null}
            </span>
            <input
              name={field.name}
              value={terms[field.name] ?? ""}
              inputMode={field.inputMode}
              autoComplete="off"
              onChange={(event) => setTerms({ ...terms, [field.name]: event.target.value })}
              className="rounded-md border border-rule bg-surface px-3 py-2 text-ink shadow-none outline-none transition-colors focus:border-cobalt"
            />
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          className="rounded-md bg-cobalt px-5 py-2 font-bold text-surface transition-opacity hover:opacity-90"
        >
          Pesquisar
        </button>
        {problem ? (
          <p role="alert" className="text-failed">
            {problem}
          </p>
        ) : null}
      </div>
    </form>
  );
}
