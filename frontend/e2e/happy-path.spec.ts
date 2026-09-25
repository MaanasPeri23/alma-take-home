import { expect, test, type APIRequestContext } from "@playwright/test";

// `make e2e` passes the seeded login from .env; the fallbacks match .env.example.
const ATTORNEY_EMAIL = process.env.E2E_EMAIL || "attorney@example.com";
const ATTORNEY_PASSWORD = process.env.E2E_PASSWORD || "change-me-locally";
const MAILPIT_URL = process.env.E2E_MAILPIT_URL || "http://localhost:8025";

// Smallest file the API accepts as a PDF: it checks the signature, not just the extension.
const PDF = Buffer.from(
  "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
    "2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n",
);

async function mailCount(request: APIRequestContext, query: string): Promise<number> {
  const response = await request.get(`${MAILPIT_URL}/api/v1/search`, { params: { query } });
  if (!response.ok()) throw new Error(`Mailpit search failed: HTTP ${response.status()}`);
  return (await response.json()).messages_count;
}

test("prospect submits, attorney downloads the resume and marks the lead reached out", async ({
  page,
  request,
}) => {
  // Unique per run, so re-runs against the same database never match an older lead.
  const suffix = String(Date.now());
  const firstName = "E2E";
  const lastName = `Tester${suffix}`;
  const email = `e2e+${suffix}@example.com`;
  const fileName = `resume-${suffix}.pdf`;

  await test.step("prospect submits the public form", async () => {
    await page.goto("/");
    await page.getByLabel("First name").fill(firstName);
    await page.getByLabel("Last name").fill(lastName);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Resume").setInputFiles({ name: fileName, mimeType: "application/pdf", buffer: PDF });
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page).toHaveURL("/thank-you");
  });

  await test.step("signed-out dashboard redirects to login", async () => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL("/login");
  });

  await test.step("attorney signs in", async () => {
    await page.getByLabel("Email").fill(ATTORNEY_EMAIL);
    await page.getByLabel("Password").fill(ATTORNEY_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL("/dashboard");
    await expect(page.getByText("Signed in as")).toBeVisible();
  });

  await test.step("new lead is first in the list, pending", async () => {
    // Newest first. Fails (never passes wrongly) if someone submits another lead mid-run.
    const firstRow = page.getByRole("row").nth(1); // row 0 is the header
    await expect(firstRow).toContainText(`${firstName} ${lastName}`);
    await expect(firstRow).toContainText("Pending");
    await firstRow.getByRole("link", { name: `${firstName} ${lastName}` }).click();
    await expect(page.getByRole("heading", { name: `${firstName} ${lastName}` })).toBeVisible();
  });

  await test.step("resume downloads with its original name", async () => {
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download" }).click();
    expect((await download).suggestedFilename()).toBe(fileName);
  });

  await test.step("marking reached out updates badge, button and history", async () => {
    await page.getByRole("button", { name: "Mark as reached out" }).click();
    await expect(page.getByRole("button", { name: "Move back to pending" })).toBeVisible();
    await expect(page.getByText("Reached out", { exact: true })).toBeVisible();
    await expect(page.getByText(/Pending → Reached out by /)).toBeVisible();
  });

  await test.step("both emails arrive in Mailpit", async () => {
    // Sent in a background task after the 201, so poll.
    await expect.poll(() => mailCount(request, `to:"${email}"`), { timeout: 15_000 }).toBe(1);
    await expect
      .poll(() => mailCount(request, `to:"${ATTORNEY_EMAIL}" subject:"New lead: ${firstName} ${lastName}"`), {
        timeout: 15_000,
      })
      .toBe(1);
  });
});
