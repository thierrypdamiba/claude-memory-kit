import Image from "next/image";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service - Amoeba Labs",
};

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-6">
          <a href="/" className="flex items-center gap-2.5">
            <Image src="/logo.png" alt="Amoeba Labs" width={36} height={36} className="h-9 w-9" />
            <Image src="/wordmark.png" alt="Amoeba Labs" width={140} height={28} className="h-6 w-auto" />
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
        <p className="text-sm text-muted-foreground mb-12">Last updated: February 14, 2026</p>

        <div className="space-y-8 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Acceptance</h2>
            <p>
              By using any Amoeba Labs product, you agree to these terms. If you don&apos;t agree,
              don&apos;t use the products.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Services</h2>
            <p>
              Amoeba Labs builds software tools including CMK, Onboard, and Airlock. These are
              provided as-is. We do our best to keep things running, but we make no guarantees
              about uptime or availability.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Your data</h2>
            <p>
              You own your data. We don&apos;t claim any rights to code, memories, or content
              you create or process through our tools. See our Privacy Policy for how we handle data.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Acceptable use</h2>
            <p>
              Don&apos;t use our products to break laws, attack other systems, or abuse our
              infrastructure. Don&apos;t reverse engineer or resell the products. Standard stuff.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Payments</h2>
            <p>
              Paid features are billed through Stripe. Refund policies vary by product. If something
              goes wrong with billing, contact us and we&apos;ll sort it out.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Limitation of liability</h2>
            <p>
              Amoeba Labs is not liable for any damages resulting from use of our products.
              This includes data loss, security incidents, or business interruption. Use our
              products at your own risk.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Changes</h2>
            <p>
              We may update these terms. Continued use after changes means you accept the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Contact</h2>
            <p>
              Questions? Reach out on{" "}
              <a href="https://x.com/thaborelli" target="_blank" rel="noopener noreferrer" className="text-foreground underline underline-offset-4">
                X
              </a>{" "}
              or{" "}
              <a href="https://github.com/thierrypdamiba" target="_blank" rel="noopener noreferrer" className="text-foreground underline underline-offset-4">
                GitHub
              </a>.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
