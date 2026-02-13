import Link from 'next/link';
import Logo from '@/components/ui/Logo';

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'Pricing', href: '#pricing' },
      { label: 'Documentation', href: '/docs' },
      { label: 'Changelog', href: '/changelog' },
      { label: 'Status', href: '/status' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '/about' },
      { label: 'Blog', href: '/blog' },
      { label: 'Careers', href: '/careers' },
      { label: 'Contact', href: 'mailto:hello@agentguard.dev' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy Policy', href: '/privacy' },
      { label: 'Terms of Service', href: '/terms' },
      { label: 'Security', href: '/security' },
      { label: 'SOC 2', href: '/security#soc2' },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-border px-6 py-12">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Logo column */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2">
              <Logo className="h-7 w-7" />
              <span className="text-sm font-semibold text-foreground">
                AgentGuard
              </span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              AI Agent Incident Response
              <br />
              for Financial Services.
            </p>
          </div>

          {/* Link columns */}
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground">
                {col.title}
              </h4>
              <ul className="mt-3 space-y-2">
                {col.links.map((link) => {
                  const isExternal =
                    link.href.startsWith('mailto:') ||
                    link.href.startsWith('#');

                  return (
                    <li key={link.label}>
                      {isExternal ? (
                        <a
                          href={link.href}
                          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                        >
                          {link.label}
                        </a>
                      ) : (
                        <Link
                          href={link.href}
                          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                        >
                          {link.label}
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-border pt-8 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} AgentGuard. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
