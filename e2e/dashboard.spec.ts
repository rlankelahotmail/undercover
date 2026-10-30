import { expect, test } from "@playwright/test";

// One file, so the tests run in order: the first ones read the fresh queue,
// and the later ones play the agent's part and change it.

test("the queue shows every claim waiting", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(26);
  await expect(page.getByLabel("Waiting: 25")).toBeVisible();
  await expect(page.getByLabel("Decided: 0")).toBeVisible();
});
