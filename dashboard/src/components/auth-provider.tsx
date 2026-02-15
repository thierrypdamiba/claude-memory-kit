"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { setTokenProvider } from "@/lib/api";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

  useEffect(() => {
    setTokenProvider(async () => {
      try {
        return await getToken();
      } catch {
        return null;
      }
    });
  }, [getToken]);

  return <>{children}</>;
}
