const FRAMEWORKS = [
  { name: 'SOX', color: 'border-red-500/20 text-red-400' },
  { name: 'PCI-DSS', color: 'border-orange-500/20 text-orange-400' },
  { name: 'FFIEC', color: 'border-yellow-500/20 text-yellow-400' },
  { name: 'NYDFS-500', color: 'border-blue-500/20 text-blue-400' },
  { name: 'DORA', color: 'border-purple-500/20 text-purple-400' },
  { name: 'EU AI Act', color: 'border-green-500/20 text-green-400' },
];

export default function ComplianceSection() {
  return (
    <section className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-5xl text-center">
        <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
          Built for Regulated Industries
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
          Continuous compliance monitoring against the regulatory frameworks that
          matter most to financial services.
        </p>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
          {FRAMEWORKS.map((fw) => (
            <div
              key={fw.name}
              className={`rounded-xl border bg-card px-8 py-5 text-center transition-all hover:border-primary/30 ${fw.color}`}
            >
              <span className="text-lg font-bold">{fw.name}</span>
            </div>
          ))}
        </div>

        <p className="mx-auto mt-10 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Automated audit trails, hash-chain verification, and exportable
          compliance reports ensure your AI operations meet regulatory
          requirements without manual overhead.
        </p>
      </div>
    </section>
  );
}
