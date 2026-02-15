import Image from "next/image";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy - Amoeba Labs",
};

export default function PrivacyPolicy() {
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
        <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-sm text-muted-foreground mb-12">Last updated: February 14, 2026</p>

        <div className="space-y-8 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">What we collect</h2>
            <p>
              Amoeba Labs products may collect usage data, account information (email, name), and
              data you provide while using our services. Each product collects only what it needs
              to function. We do not sell your data.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">How we use it</h2>
            <p>
              We use collected data to operate, maintain, and improve our products. This includes
              authenticating users, processing payments, and debugging issues. We may use anonymized,
              aggregated data to understand usage patterns.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Third-party services</h2>
            <p>
              Our products use third-party services including Clerk (authentication), Stripe (payments),
              and various cloud hosting providers. These services have their own privacy policies.
              We also use the Anthropic API, and data sent to the API is subject to
              Anthropic&apos;s usage policies.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Data storage</h2>
            <p>
              Products that offer local-first storage (like CMK) keep your data on your machine by default.
              Cloud sync features are opt-in. When you use cloud features, data is stored on secured
              infrastructure with encryption at rest and in transit.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Your rights</h2>
            <p>
              You can request deletion of your account and associated data at any time by contacting us.
              For products with local storage, you control your own data directly.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3">Contact</h2>
            <p>
              Questions about this policy? Reach out on{" "}
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
