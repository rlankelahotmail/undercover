import { expect, test } from "@playwright/test";

// One file, so the tests run in order: the first ones read the fresh queue,
// and the last one plays the agent's part and changes it.

test("the queue shows every claim waiting", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(26);
  await expect(page.getByLabel("Waiting: 25")).toBeVisible();
  await expect(page.getByLabel("Decided: 0")).toBeVisible();
});

test("a claim opens from the queue in full", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
  await expect(page.getByText(/^My flight home from Rome/)).toBeVisible();
  const items = page.locator("section", {
    has: page.getByRole("heading", { name: "Items claimed" }),
  });
  await expect(items.getByRole("row")).toHaveCount(5);
  await expect(page.locator(".documents article")).toHaveCount(4);
  await expect(page.getByText("Premium", { exact: true })).toBeVisible();
  await expect(page.getByText("CLM-0412")).toBeVisible();
});

test("the instructions are read only", async ({ page }) => {
  await page.goto("/#/instructions");
  const text = page.locator("pre.instructions");
  await expect(text).toContainText("# The UnderCover Agent");
  await expect(text).toContainText(
    "# UnderCover Travel Insurance: Policy Wording",
  );
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByRole("button")).toHaveCount(0);
});

test("a handler signs off a payout over $1,000", async ({ page, request }) => {
  const claim = "/api/claims/CLM-1003";
  await request.post(`${claim}/start`);
  for (const step of [
    { kind: "call", name: "get_claim", content: '{"claim_id": "CLM-1003"}' },
    { kind: "result", name: "get_claim", content: '{"claim_id": "CLM-1003"}' },
    { kind: "message", name: "agent", content: "Reading the policy next." },
  ]) {
    await request.post(`${claim}/steps`, {
      data: { thread_id: "e2e", ...step },
    });
  }

  await page.goto("/#/claims/CLM-1003");
  await expect(page.locator(".title .badge")).toHaveText("In progress");
  await expect(page.locator("li.step")).toHaveText([
    /^Calls get_claim/,
    /^Result from get_claim/,
    "Reading the policy next.",
  ]);

  await request.post(`${claim}/decision`, {
    data: {
      outcome: "approve",
      payout: 1250,
      reason: "The fall and the treatment are covered.",
      policy_section: "Section 7, Emergency Medical",
    },
  });
  await expect(page.locator(".title .badge")).toHaveText(
    "Waiting for sign-off",
  );
  await expect(
    page.getByText("The fall and the treatment are covered."),
  ).toBeVisible();
  await expect(page.getByText("Section 7, Emergency Medical")).toBeVisible();

  await page
    .getByRole("combobox", { name: "Handler" })
    .selectOption({ label: "Dana Whitfield" });
  await page
    .getByRole("button", { name: "Sign off and pay $1,250.00" })
    .click();
  await expect(page.locator(".title .badge")).toHaveText("Decided");
  await expect(page.locator("p", { hasText: /^Paid/ })).toContainText(
    "$1,250.00",
  );
  await expect(
    page.locator("p", { hasText: /^Signed off by Dana Whitfield/ }),
  ).toBeVisible();
});
