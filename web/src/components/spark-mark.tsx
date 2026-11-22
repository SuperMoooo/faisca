/**
 * The mark: a catalogue card in cobalt with the acute accent of "Faísca" as
 * an amber spark. The same drawing is public/icon.svg, for the PWA icon.
 */
export function SparkMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" focusable="false">
      <rect x="3" y="7" width="26" height="20" rx="2.5" fill="var(--cobalt)" />
      <circle cx="16" cy="23" r="1.6" fill="var(--surface)" />
      <path d="M8 13h16M8 17h10" stroke="var(--surface)" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M18 5.4 24.2 1.2" stroke="var(--spark)" strokeWidth="3.4" strokeLinecap="round" />
    </svg>
  );
}
