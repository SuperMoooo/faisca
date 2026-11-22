import { Suspense } from "react";

import { SearchPage } from "@/components/search/search-page";

/**
 * The search page. It reads the search from the URL, so it renders in the
 * browser inside a Suspense boundary (the static export cannot know the query).
 */
export default function Home() {
  return (
    <Suspense fallback={null}>
      <SearchPage />
    </Suspense>
  );
}
