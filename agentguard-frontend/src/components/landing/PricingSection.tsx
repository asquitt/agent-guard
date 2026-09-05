import { Archive, LockKeyhole, PackageOpen } from 'lucide-react';

const ARCHIVE_BOUNDARIES = [
  {
    icon: Archive,
    title: 'Preservation only',
    description: 'The repository and selected public material remain available as archived reference.',
  },
  {
    icon: LockKeyhole,
    title: 'Standalone activity frozen',
    description: 'Customer acquisition, registration, deployment, and provider/runtime use are not authorized.',
  },
  {
    icon: PackageOpen,
    title: 'Bounded extraction',
    description: 'Assets may move only through a separately authorized extraction with a named consumer.',
  },
];

export default function ArchiveDispositionSection() {
  return (
    <section id="archive" className="border-y border-border bg-muted/20 px-6 py-24">
      <div className="mx-auto max-w-5xl">
        <div className="text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-primary">
            Portfolio disposition
          </p>
          <h2 className="mt-3 text-3xl font-bold text-foreground sm:text-4xl">
            Standalone Product Mothballed
          </h2>
          <p className="mx-auto mt-4 max-w-2xl leading-relaxed text-muted-foreground">
            No prices, plans, trials, pilots, or workspaces are offered. The
            archived interface does not establish a hosted service, a production
            deployment, or current runtime availability.
          </p>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {ARCHIVE_BOUNDARIES.map((boundary) => (
            <article
              key={boundary.title}
              className="rounded-xl border border-border bg-card p-6"
            >
              <boundary.icon className="h-6 w-6 text-primary" aria-hidden="true" />
              <h3 className="mt-4 text-base font-semibold text-foreground">
                {boundary.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {boundary.description}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
