import Link from "next/link";

/** Any address the app does not have (the static export serves it as 404.html). */
export default function NotFound() {
  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-title font-bold">Esta página não existe</h1>
      <p>
        <Link href="/" className="font-semibold text-cobalt">
          Voltar à pesquisa
        </Link>
      </p>
    </div>
  );
}
