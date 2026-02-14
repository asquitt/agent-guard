import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'AgentGuard privacy policy — how we collect, use, and protect your data.',
};

export default function PrivacyPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">
          Privacy Policy
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Effective: February 1, 2026
        </p>

        <div className="mt-12 space-y-10">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              1. Introduction
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              AgentGuard, Inc. (&ldquo;AgentGuard,&rdquo; &ldquo;we,&rdquo;
              &ldquo;us&rdquo;) operates the AgentGuard platform for AI agent
              security monitoring and incident response. This Privacy Policy
              explains how we collect, use, disclose, and safeguard your
              information when you use our platform and services.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              2. Information We Collect
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              <strong className="text-foreground">Account Information:</strong>{' '}
              When you create an account, we collect your name, email address,
              organization name, and billing information.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              <strong className="text-foreground">Usage Data:</strong> We
              collect information about how you interact with our platform,
              including pages visited, features used, and actions taken.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              <strong className="text-foreground">LLM Traffic Data:</strong>{' '}
              When you route AI agent traffic through our proxy, we process
              request and response payloads to perform security analysis. This
              data is processed in accordance with your data processing
              agreement and retention settings.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              <strong className="text-foreground">Technical Data:</strong> We
              collect IP addresses, browser type, device information, and log
              data for security and performance purposes.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              3. How We Use Your Information
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              We use collected information to: provide and maintain our
              platform; detect and prevent security threats in your AI agent
              traffic; generate compliance reports and audit trails; send
              alerts and notifications; improve our detection algorithms; and
              comply with legal obligations.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              4. Data Sharing
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              We do not sell your personal information. We may share data with:
              infrastructure providers necessary to operate our platform;
              payment processors for billing; and law enforcement when required
              by law. All third-party processors are bound by data processing
              agreements.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              5. Data Retention
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Account data is retained for the duration of your subscription
              and for 30 days after termination. LLM traffic data retention is
              configurable per your organization&apos;s settings (7, 30, 90
              days, or custom). Audit logs are retained for the period required
              by applicable regulations.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              6. Data Security
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              We implement industry-standard security measures including
              encryption at rest and in transit (AES-256 and TLS 1.3),
              role-based access controls, tenant isolation, network
              segmentation, and continuous monitoring. See our{' '}
              <a
                href="/security"
                className="font-medium text-primary hover:text-primary/80"
              >
                Security page
              </a>{' '}
              for details.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              7. Your Rights
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Depending on your jurisdiction, you may have the right to:
              access, correct, or delete your personal data; restrict or object
              to processing; data portability; and lodge a complaint with a
              supervisory authority. To exercise these rights, contact us at{' '}
              <a
                href="mailto:privacy@agentguard.dev"
                className="font-medium text-primary hover:text-primary/80"
              >
                privacy@agentguard.dev
              </a>
              .
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              8. International Data Transfers
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Our platform is hosted in the United States. For customers
              subject to GDPR or other data residency requirements, we offer
              configurable data residency controls. Contact us for details
              about our Standard Contractual Clauses and data transfer
              mechanisms.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              9. Changes to This Policy
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              We may update this Privacy Policy from time to time. We will
              notify you of material changes by email or through the platform.
              Your continued use of AgentGuard after changes constitutes
              acceptance of the revised policy.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              10. Contact Us
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              For questions about this Privacy Policy, contact us at{' '}
              <a
                href="mailto:privacy@agentguard.dev"
                className="font-medium text-primary hover:text-primary/80"
              >
                privacy@agentguard.dev
              </a>
              .
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
