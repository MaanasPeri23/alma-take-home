"use client";

import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { api } from "@/lib/client";

type Attorney = components["schemas"]["AttorneyOut"];

// Shows who is signed in. A 401 from /me (stale cookie) is handled by the client middleware,
// which logs out and redirects to /login.
export default function AccountMenu() {
  const [attorney, setAttorney] = useState<Attorney | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    api.GET("/api/auth/me").then(({ data }) => {
      if (data) setAttorney(data);
    }, () => {});
  }, []);

  async function signOut() {
    setSigningOut(true);
    try {
      await api.POST("/api/auth/logout");
    } catch {
      // Logout always clears the cookie server-side; go to /login regardless.
    }
    // Full navigation so no cached dashboard data survives sign-out.
    window.location.replace("/login");
  }

  return (
    <div className="flex items-center gap-3 text-sm">
      {attorney && <span className="text-zinc-600">Signed in as {attorney.name}</span>}
      <button
        type="button"
        onClick={signOut}
        disabled={signingOut}
        className="rounded-md border border-zinc-300 px-3 py-1 hover:bg-zinc-100 hover:text-zinc-900 disabled:opacity-50"
      >
        Log out
      </button>
    </div>
  );
}
