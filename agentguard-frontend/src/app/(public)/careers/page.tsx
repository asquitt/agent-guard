import type { Metadata } from 'next';
import {
  Globe,
  TrendingUp,
  Heart,
  BookOpen,
  ArrowRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Careers',
  description:
    'Join AgentGuard and help secure the future of AI in financial services.',
  openGraph: {
    title: 'Careers at AgentGuard',
    description: 'Join AgentGuard and help secure the future of AI in financial services.',
  },
};

interface Benefit {
  icon: LucideIcon;
  title: string;
  description: string;
}

const BENEFITS: Benefit[] = [
  {
    icon: Globe,
    title: 'Remote-First',
    description: 'Work from anywhere. We hire the best talent regardless of location.',
  },
  {
    icon: TrendingUp,
    title: 'Meaningful Equity',
    description: 'Early-stage equity so you share in what we build together.',
  },
  {
    icon: Heart,
    title: 'Health & Wellness',
    description: 'Comprehensive health, dental, and vision coverage for you and your family.',
  },
  {
    icon: BookOpen,
    title: 'Learning Budget',
    description: 'Annual stipend for conferences, courses, and books to keep growing.',
  },
];

interface Role {
  title: string;
  team: string;
  location: string;
}

const OPEN_ROLES: Role[] = [
  { title: 'Senior Backend Engineer', team: 'Platform', location: 'Remote' },
  { title: 'Security Researcher', team: 'Detection', location: 'Remote' },
  { title: 'Solutions Engineer', team: 'Customer Success', location: 'Remote' },
];

export default function CareersPage() {
  return (
    <>
      {/* Hero */}
      <section className="px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Join AgentGuard
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            We&apos;re building the security platform for the AI agent era.
            If you&apos;re passionate about AI, security, and financial
            services — we want to hear from you.
          </p>
        </div>
      </section>

      {/* Benefits */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-foreground">
            Why AgentGuard
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {BENEFITS.map((b) => (
              <div
                key={b.title}
                className="rounded-xl border border-border bg-card p-6"
              >
                <b.icon className="mb-4 h-6 w-6 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">
                  {b.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {b.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Open roles */}
      <section className="border-t border-border px-6 py-24">
        <div className="mx-auto max-w-3xl">
          <h2 className="mb-8 text-center text-3xl font-bold text-foreground">
            Open Positions
          </h2>
          <div className="space-y-3">
            {OPEN_ROLES.map((role) => (
              <a
                key={role.title}
                href="mailto:careers@agentguard.dev"
                className="flex items-center justify-between rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/30"
              >
                <div>
                  <p className="font-semibold text-foreground">{role.title}</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {role.team} &middot; {role.location}
                  </p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </a>
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-muted-foreground">
            Don&apos;t see your role?{' '}
            <a
              href="mailto:careers@agentguard.dev"
              className="font-medium text-primary hover:text-primary/80"
            >
              Send us your resume
            </a>
          </p>
        </div>
      </section>
    </>
  );
}
