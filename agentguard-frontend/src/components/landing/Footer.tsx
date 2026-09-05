import Link from 'next/link';
import Logo from '@/components/ui/Logo';

const COLUMNS = [
  {
    title: 'Archive',
    links: [
      { label: 'Disposition', href: '/#archive' },
      { label: 'Archived Reference', href: '/docs' },
      { label: 'Development History', href: '/changelog' },
      { label: 'Generic Status Surface', href: '/status' },
    ],
  },
  {
    title: 'Project',
    links: [
      { label: 'About the Archive', href: '/about' },
      { label: 'Archived Blog', href: '/blog' },
      { label: 'Archived Careers', href: '/careers' },
      { label: 'Existing Account', href: '/login' },
    ],
  },
  {
    title: 'Reference',
    links: [
      { label: 'Archived Data Notice', href: '/privacy' },
      { label: 'Archived Terms Notice', href: '/terms' },
      { label: 'Security Reference', href: '/security' },
      { label: 'Assurance Caveats', href: '/security#assurance' },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-border px-6 py-12">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2">
              <Logo className="h-7 w-7" />
              <span className="text-sm font-semibold text-foreground">
                AgentGuard
              </span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Mothballed standalone project.
              <br />
              Archived reference only.
            </p>
          </div>

          {COLUMNS.map((column) => (
            <div key={column.title}>
              <h4 className="text-sm font-semibold text-foreground">
                {column.title}
              </h4>
              <ul className="mt-3 space-y-2">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-border pt-8 text-center text-sm text-muted-foreground">
          Archived AgentGuard source reference · {new Date().getFullYear()}
        </div>
      </div>
    </footer>
  );
}
