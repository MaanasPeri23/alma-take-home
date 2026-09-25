import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

// Typed API client. The types in lib/api/ are generated from FastAPI's OpenAPI spec
// (`make gen-client`), so a backend change that breaks the frontend fails to compile.
// Same-origin baseUrl: requests go to /api/* and Next.js proxies them to FastAPI.
export const api = createClient<paths>({ baseUrl: "" });

// Wrong credentials on these are ordinary form errors, not an expired session.
const NO_SIGN_OUT_ON_401 = ["/api/auth/login", "/api/auth/logout"];

let signingOut = false;

// Any other 401 means the session is missing or stale. The cookie is httpOnly, so JS can't
// delete it; logout is the only way to clear it. Without this, proxy.ts would keep sending a
// stale cookie to /dashboard and the page would keep failing.
api.use({
  async onResponse({ request, response }) {
    if (response.status !== 401 || typeof window === "undefined") return;
    if (NO_SIGN_OUT_ON_401.includes(new URL(request.url, window.location.origin).pathname)) return;
    // Several calls can 401 at once; sign out and redirect only once.
    if (signingOut) return;
    signingOut = true;
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Still send them to /login; the next login overwrites the cookie anyway.
    }
    window.location.replace("/login");
  },
});
