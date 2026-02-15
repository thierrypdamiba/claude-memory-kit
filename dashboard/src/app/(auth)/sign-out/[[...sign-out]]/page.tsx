"use client";

import { useClerk } from "@clerk/nextjs";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SignOutPage() {
  const { signOut } = useClerk();
  const router = useRouter();

  useEffect(() => {
    signOut().then(() => {
      router.push("/");
    });
  }, [signOut, router]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "#FAF9F7" }}
    >
      <div className="text-center">
        <p
          className="text-[15px]"
          style={{ color: "var(--muted)" }}
        >
          Signing out...
        </p>
      </div>
    </div>
  );
}
