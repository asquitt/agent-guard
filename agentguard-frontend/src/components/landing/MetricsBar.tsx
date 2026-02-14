const METRICS = [
  { value: '<2ms', label: 'Added Latency' },
  { value: '99.9%', label: 'Uptime SLA' },
  { value: '6', label: 'Compliance Frameworks' },
  { value: '50M+', label: 'Requests Secured' },
];

export default function MetricsBar() {
  return (
    <section className="border-y border-border bg-card/50 px-6 py-16">
      <div className="mx-auto max-w-5xl">
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {METRICS.map((m) => (
            <div key={m.label} className="text-center">
              <p className="text-3xl font-bold text-primary sm:text-4xl">
                {m.value}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{m.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
