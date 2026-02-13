const INSTITUTIONS = [
  'Meridian Capital',
  'Atlas Financial',
  'Pinnacle Bank',
  'Vertex Securities',
  'Horizon Trust',
];

export default function TrustBar() {
  return (
    <section className="border-y border-border bg-card/50 px-6 py-12">
      <div className="mx-auto max-w-7xl">
        <p className="mb-8 text-center text-sm font-medium uppercase tracking-wider text-muted-foreground/60">
          Trusted by teams securing AI agents at leading financial institutions
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6">
          {INSTITUTIONS.map((name) => (
            <span
              key={name}
              className="text-lg font-semibold text-muted-foreground/30 transition-colors hover:text-muted-foreground/50"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
