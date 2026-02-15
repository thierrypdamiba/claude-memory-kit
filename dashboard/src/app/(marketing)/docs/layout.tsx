import { DocsSidebar } from "@/components/marketing/docs-sidebar";

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="max-w-6xl mx-auto px-6">
      <div className="flex min-h-[calc(100vh-3.5rem)]">
        <DocsSidebar />
        <div className="flex-1 py-8 pl-10">{children}</div>
      </div>
    </div>
  );
}
