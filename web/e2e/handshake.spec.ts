import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

// Full claim -> validation -> K-Asset approval with real testnet/devnet keystores.
// Requires: seeded devnet, `.demo/keystores-devnet/`, `.demo/seed-devnet.json`.
test.skip(
  process.env.RGEN_E2E_JOURNEY !== "1",
  "set RGEN_E2E_JOURNEY=1 after `make demo-seed`",
);

const repo = resolve(process.cwd(), "..");
const password = "rgen-demo-password";
const seed = JSON.parse(
  readFileSync(resolve(repo, ".demo", "seed-devnet.json"), "utf8"),
) as {
  credentials: { validator: string; approver: string };
};

function keystore(name: string): string {
  return readFileSync(resolve(repo, ".demo", "keystores-devnet", `${name}.json`), "utf8");
}

async function importWallet(page: Page, name: string): Promise<void> {
  await page.getByRole("button", { name: "Import", exact: true }).click();
  await page.getByLabel("Keystore JSON").fill(keystore(name));
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Import and unlock" }).click();
  await expect(page.locator(".wallet-chip")).toContainText("Lock");
}

async function lock(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Lock", exact: true }).click();
  await expect(page.getByRole("button", { name: "Import", exact: true })).toBeVisible();
}

test("claim, validate and approve through the real contracts", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".banner.good")).toContainText("Root resolved (9/9 keys)", {
    timeout: 60_000,
  });

  await importWallet(page, "alice");
  await page.getByRole("link", { name: "Claims" }).click();
  await page.getByRole("link", { name: "New claim" }).click();
  await page.getByLabel("Work title").fill("Playwright bridge claim");
  await page.getByLabel("Statement of work").fill("Inspect twelve bays in the e2e run.");
  await page.getByRole("button", { name: "Create claim" }).click();
  await expect(page).toHaveURL(/#\/claims\/rho:id:/, { timeout: 120_000 });
  const claimUri = decodeURIComponent(page.url().split("#/claims/")[1] ?? "");

  await lock(page);
  await importWallet(page, "bob");
  await page.goto(`/#/claims/${claimUri}`);
  await page.getByLabel("Credential URI").fill(seed.credentials.validator);
  await page.getByRole("button", { name: "Validate claim" }).click();
  await expect(page.getByRole("link", { name: "open K-Asset" })).toBeVisible({
    timeout: 120_000,
  });

  await lock(page);
  await importWallet(page, "carol");
  await page.getByRole("link", { name: "open K-Asset" }).click();
  await page.getByLabel("Approver credential URI").fill(seed.credentials.approver);
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.locator(".panel-head .pill").first()).toHaveText("approved", {
    timeout: 120_000,
  });
});
