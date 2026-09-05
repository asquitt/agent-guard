import Link from 'next/link';
import Logo from '@/components/ui/Logo';

const NAV_LINKS = [
  { label: 'Archive', href: '/#archive' },
  { label: 'Reference', href: '/docs' },
  { label: 'Security', href: '/security' },
  { label: 'Status', href: '/status' },
];

export default function LandingNav() {
  return (
    <nav className="fixed top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo className="h-8 w-8" />
          <span className="text-sm font-semibold text-foreground">AgentGuard</span>
          <span className="hidden rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground sm:inline">
            Archived
          </span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Existing Account
          </Link>
          <Link
            href="/about"
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            Archive Details
          </Link>
        </div>
      </div>
    </nav>
  );
}
