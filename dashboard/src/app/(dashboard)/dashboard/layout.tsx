import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="ml-56 flex-1 flex flex-col">
        <TopBar />
        <main className="flex-1 px-10 py-8">{children}</main>
      </div>
    </div>
  );
}
