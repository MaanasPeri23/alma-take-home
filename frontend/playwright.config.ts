import { defineConfig, devices } from "@playwright/test";

// Runs against a stack that's already up (`make up`), like `make test`. No webServer here.
// E2E_BASE_URL overrides the target, e.g. a dev server on another port.
export default defineConfig({
  testDir: "e2e",
  // Generous: on a fresh `make up`, `next dev` compiles each route on its first visit.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
