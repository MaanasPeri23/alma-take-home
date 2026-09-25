import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

// Typed API client. The types in lib/api/ are generated from FastAPI's OpenAPI spec
// (`make gen-client`), so a backend change that breaks the frontend fails to compile.
// Same-origin baseUrl: requests go to /api/* and Next.js proxies them to FastAPI.
export const api = createClient<paths>({ baseUrl: "" });
