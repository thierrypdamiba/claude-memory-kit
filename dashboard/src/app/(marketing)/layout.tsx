import { MarketingNav } from "@/components/marketing-nav";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <MarketingNav />
      <main className="pt-14">{children}</main>
    </>
  );
}
