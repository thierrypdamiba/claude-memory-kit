"use client";

import { UserButton as ClerkUserButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";

export function UserButton() {
  const hasClerk = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!hasClerk) return null;

  return <AuthAwareButton />;
}

function AuthAwareButton() {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) return null;

  if (!isSignedIn) {
    return (
      <Link
        href="/sign-in"
        className="text-[13px] font-medium px-2.5 py-1 rounded-[var(--radius-sm)]"
        style={{
          color: "var(--accent)",
          background: "rgba(122, 134, 154, 0.08)",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(122, 134, 154, 0.14)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "rgba(122, 134, 154, 0.08)";
        }}
      >
        Sign in
      </Link>
    );
  }

  return (
    <ClerkUserButton
      appearance={{
        elements: {
          avatarBox: "w-7 h-7",
        },
      }}
    />
  );
}
