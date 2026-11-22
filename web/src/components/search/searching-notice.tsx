import { SparkMark } from "../spark-mark";

/**
 * Shown while the targets are being asked. Live searches take from one
 * second to half a minute (a slow Z39.50 server), so it says so instead of
 * pretending to measure progress. The flickering spark is the page's only
 * animation, and it stops under reduced motion.
 */
export function SearchingNotice({ text }: { text: string }) {
  return (
    <div role="status" className="flex items-center gap-3 rounded-lg border border-rule bg-surface px-4 py-3">
      <SparkMark className="h-6 w-6 motion-safe:animate-pulse" />
      <p>
        {text}
        <span className="block text-small text-muted">Pode demorar até meio minuto, se algum catálogo estiver lento.</span>
      </p>
    </div>
  );
}
