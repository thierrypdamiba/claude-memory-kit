"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useCallback } from "react";

export type Scope = "workspace" | "project" | "person";

export function useScope() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const scope = (searchParams.get("scope") as Scope) || "workspace";

  const setScope = useCallback(
    (newScope: Scope) => {
      const params = new URLSearchParams(searchParams.toString());
      if (newScope === "workspace") {
        params.delete("scope");
      } else {
        params.set("scope", newScope);
      }
      const qs = params.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname);
    },
    [searchParams, router, pathname]
  );

  return { scope, setScope };
}
