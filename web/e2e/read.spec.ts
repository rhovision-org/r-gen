import { expect, test } from "@playwright/test";

// Read-only journey. It needs a running, seeded devnet and the built app.
test.skip(process.env.RGEN_E2E !== "1", "set RGEN_E2E=1 with a seeded devnet");

test("the overview resolves the Root and reads real catalogue statuses", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Browse without a wallet" }).click();
  await expect(page.locator(".banner.good")).toContainText("Root resolved (9/9 keys)", {
    timeout: 60_000,
  });
  await expect(page.getByText("Seeded bridge inspection")).toBeVisible();
  const approved = page.locator(".card", { hasText: "Approved K-Asset" });
  await expect(approved).toContainText("approved", { timeout: 60_000 });
  await approved.getByRole("link", { name: "open" }).click();
  await expect(page.locator("h1")).toHaveText("K-Asset");
  await expect(page.locator(".panel-head .pill").first()).toHaveText("approved");
  await expect(page.getByText("free read", { exact: false }).first()).toBeVisible();
});
