"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useBasket } from "@/lib/api/queries";

import { SparkMark } from "./spark-mark";

const NAVIGATION = [
  { href: "/", label: "Pesquisa" },
  { href: "/cesto/", label: "Cesto" },
  { href: "/definicoes/", label: "Definições" },
] as const;

/** The top bar: the name, the three places, and how many records wait in the basket. */
export function AppHeader() {
  const pathname = usePathname();
  const { data: basket } = useBasket();

  return (
    <header className="border-b border-rule bg-surface">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-4 py-3 sm:gap-6 sm:px-6">
        <Link href="/" className="flex items-center gap-2 text-ink" aria-label="Faísca, página de pesquisa">
          <SparkMark className="h-7 w-7" />
          {/* On the narrowest phones the mark alone leaves room for all three places. */}
          <span className="hidden text-lead font-bold tracking-tight min-[400px]:inline">Faísca</span>
        </Link>
        <nav aria-label="Principal" className="ml-auto">
          <ul className="flex items-center gap-0.5 sm:gap-2">
            {NAVIGATION.map((item) => {
              const isCurrent = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={isCurrent ? "page" : undefined}
                    className={`flex items-center gap-1.5 rounded-md px-2 py-1.5 font-semibold transition-colors sm:px-3 ${
                      isCurrent ? "bg-cobalt-soft text-cobalt" : "text-muted hover:text-ink"
                    }`}
                  >
                    {item.label}
                    {item.href === "/cesto/" && basket && basket.count > 0 ? (
                      <span
                        className="min-w-5 rounded-full bg-cobalt px-1.5 text-center text-small font-bold leading-5 text-surface"
                        aria-label={`${basket.count} no cesto`}
                      >
                        {basket.count}
                      </span>
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
