import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service - AgentGuard',
  description: 'AgentGuard terms of service governing use of our platform.',
};

export default function TermsPage() {
  return (
    <section className="px-6 py-24">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">
          Terms of Service
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Effective: February 1, 2026
        </p>

        <div className="mt-12 space-y-10">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              1. Acceptance of Terms
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              By accessing or using the AgentGuard platform
              (&ldquo;Service&rdquo;), you agree to be bound by these Terms
              of Service (&ldquo;Terms&rdquo;). If you are using the Service
              on behalf of an organization, you represent that you have the
              authority to bind that organization to these Terms.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              2. Description of Service
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              AgentGuard provides AI agent security monitoring, threat
              detection, compliance monitoring, and incident response tools
              for organizations operating AI agents in regulated environments.
              The Service includes a real-time LLM proxy, detection engine,
              dashboard, alerting system, and related APIs and SDKs.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              3. User Accounts
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              You are responsible for maintaining the confidentiality of your
              account credentials and for all activities that occur under your
              account. You must notify us immediately of any unauthorized use.
              AgentGuard reserves the right to suspend or terminate accounts
              that violate these Terms.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              4. Acceptable Use
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              You agree not to: reverse engineer, decompile, or disassemble
              the Service; use the Service to violate any applicable law or
              regulation; attempt to gain unauthorized access to any systems
              or networks; transmit malware or harmful code through the
              Service; or resell or sublicense access without written
              permission.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              5. Data Processing
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              AgentGuard processes data in accordance with our{' '}
              <a
                href="/privacy"
                className="font-medium text-primary hover:text-primary/80"
              >
                Privacy Policy
              </a>{' '}
              and any applicable Data Processing Agreement (DPA). For
              enterprise customers, custom DPAs are available upon request.
              You retain ownership of all data you transmit through the
              Service.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              6. Intellectual Property
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              The Service, including all software, algorithms, designs, and
              documentation, is owned by AgentGuard, Inc. and protected by
              intellectual property laws. Your subscription grants you a
              limited, non-exclusive, non-transferable license to use the
              Service during your subscription term.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              7. Payment Terms
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Subscription fees are billed monthly or annually as specified
              in your plan. All fees are non-refundable except as required by
              law. We may change pricing with 30 days&apos; notice. Failure
              to pay may result in suspension of Service access.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              8. Service Level Agreement
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              AgentGuard targets 99.9% uptime for the platform. Enterprise
              customers may negotiate custom SLAs. Scheduled maintenance
              windows will be communicated in advance. Current system status
              is available at{' '}
              <a
                href="/status"
                className="font-medium text-primary hover:text-primary/80"
              >
                our status page
              </a>
              .
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              9. Limitation of Liability
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              To the maximum extent permitted by law, AgentGuard&apos;s total
              liability for any claims arising from the Service shall not
              exceed the fees paid by you in the twelve months preceding the
              claim. AgentGuard shall not be liable for indirect, incidental,
              special, consequential, or punitive damages.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              10. Termination
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Either party may terminate the subscription with 30 days&apos;
              written notice. AgentGuard may immediately terminate for
              material breach of these Terms. Upon termination, you may
              export your data within 30 days. After that period, data will
              be deleted in accordance with our retention policies.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              11. Governing Law
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              These Terms are governed by the laws of the State of Delaware,
              without regard to conflict of law principles. Any disputes
              shall be resolved in the state or federal courts located in
              Delaware.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground">
              12. Contact
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              For questions about these Terms, contact us at{' '}
              <a
                href="mailto:legal@agentguard.dev"
                className="font-medium text-primary hover:text-primary/80"
              >
                legal@agentguard.dev
              </a>
              .
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
