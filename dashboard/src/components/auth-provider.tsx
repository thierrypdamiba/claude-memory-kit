"use client";

import { useEffect } from "react";
import { authClient } from "@/lib/auth-client";
import { setTokenProvider } from "@/lib/api";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    setTokenProvider(async () => {
      try {
        const res = await authClient.$fetch("/token", { method: "GET" });
        const data = res.data as { token?: string } | null;
        return data?.token ?? null;
      } catch {
        return null;
      }
    });
  }, []);

  return <>{children}</>;
}
