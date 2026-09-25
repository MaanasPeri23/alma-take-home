import type { NextConfig } from "next";

// The browser only ever talks to this origin; Next.js proxies /api/* to FastAPI.
// That avoids CORS and cross-port cookie issues. FastAPI still enforces auth.
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // FastAPI serves liveness at /health (not under /api), so map it explicitly.
      { source: "/api/health", destination: `${apiUrl}/health` },
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
