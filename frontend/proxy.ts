import { NextResponse, type NextRequest } from "next/server";

// Optimistic check only: send signed-out visitors to /login before rendering the dashboard.
// The cookie is httpOnly and may be stale; the API is the real auth check. /login is never
// guarded, so a stale cookie can't cause a redirect loop.
export function proxy(request: NextRequest) {
  if (!request.cookies.has("session")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard", "/dashboard/:path*"],
};
