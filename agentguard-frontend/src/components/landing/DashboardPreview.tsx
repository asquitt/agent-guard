const MOCK_METRICS = [
  { label: 'Total Requests', value: '1.2M', change: '+12.3%' },
  { label: 'Incidents', value: '47', change: '-8.1%' },
  { label: 'Detection Rate', value: '99.7%', change: '+0.3%' },
  { label: 'Avg Latency', value: '2.1ms', change: '-15%' },
];

const MOCK_INCIDENTS = [
  {
    id: 'INC-1042',
    type: 'PII Leak',
    severity: 'critical',
    agent: 'CS Bot',
    time: '2m ago',
  },
  {
    id: 'INC-1041',
    type: 'Prompt Injection',
    severity: 'high',
    agent: 'Trade Assist',
    time: '8m ago',
  },
  {
    id: 'INC-1040',
    type: 'Hallucination',
    severity: 'medium',
    agent: 'Advisor',
    time: '14m ago',
  },
  {
    id: 'INC-1039',
    type: 'Cost Anomaly',
    severity: 'low',
    agent: 'Data Agent',
    time: '31m ago',
  },
];

const SEV_COLORS: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400',
  high: 'bg-orange-500/10 text-orange-400',
  medium: 'bg-yellow-500/10 text-yellow-400',
  low: 'bg-green-500/10 text-green-400',
};

export default function DashboardPreview() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
            Built for Security Teams
          </h2>
          <p className="mt-4 text-muted-foreground">
            A purpose-built command center for AI agent security operations.
          </p>
        </div>

        {/* Browser window mockup */}
        <div className="overflow-hidden rounded-xl border border-border shadow-2xl shadow-primary/5">
          {/* Title bar */}
          <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
            <div className="flex gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500/60" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/60" />
              <div className="h-3 w-3 rounded-full bg-green-500/60" />
            </div>
            <div className="ml-4 flex-1 rounded-md bg-background px-3 py-1 text-xs text-muted-foreground">
              app.agentguard.dev/dashboard
            </div>
          </div>

          {/* Mock dashboard */}
          <div className="bg-background p-4 sm:p-6">
            {/* Metric cards */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {MOCK_METRICS.map((m) => (
                <div
                  key={m.label}
                  className="rounded-lg border border-border bg-card p-4"
                >
                  <p className="text-xs text-muted-foreground">{m.label}</p>
                  <p className="mt-1 text-xl font-semibold text-foreground">
                    {m.value}
                  </p>
                  <p className="mt-0.5 text-xs text-green-400">{m.change}</p>
                </div>
              ))}
            </div>

            {/* Incident table */}
            <div className="mt-4 overflow-hidden rounded-lg border border-border bg-card">
              <div className="border-b border-border px-4 py-3">
                <p className="text-sm font-semibold text-foreground">
                  Recent Incidents
                </p>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="px-4 py-2 text-xs font-medium uppercase text-muted-foreground">
                      ID
                    </th>
                    <th className="px-4 py-2 text-xs font-medium uppercase text-muted-foreground">
                      Type
                    </th>
                    <th className="hidden px-4 py-2 text-xs font-medium uppercase text-muted-foreground sm:table-cell">
                      Severity
                    </th>
                    <th className="hidden px-4 py-2 text-xs font-medium uppercase text-muted-foreground md:table-cell">
                      Agent
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase text-muted-foreground">
                      Time
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_INCIDENTS.map((inc) => (
                    <tr
                      key={inc.id}
                      className="border-b border-border last:border-0"
                    >
                      <td className="px-4 py-2.5 font-mono text-xs text-foreground">
                        {inc.id}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-foreground">
                        {inc.type}
                      </td>
                      <td className="hidden px-4 py-2.5 sm:table-cell">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${SEV_COLORS[inc.severity]}`}
                        >
                          {inc.severity}
                        </span>
                      </td>
                      <td className="hidden px-4 py-2.5 text-xs text-muted-foreground md:table-cell">
                        {inc.agent}
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-muted-foreground">
                        {inc.time}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
