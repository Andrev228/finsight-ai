import { expect, test } from "@playwright/test";

test("disconnected users are redirected from chat to connect", async ({
  page,
}) => {
  await page.goto("/chat");

  await expect(page).toHaveURL("/");
  await expect(
    page.getByRole("button", { name: "Connect a bank" }),
  ).toBeVisible();
});

test("connected browser sessions can open chat", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => sessionStorage.setItem("bankConnected", "true"));

  await page.goto("/chat");

  await expect(
    page.getByRole("heading", { name: "Ask about your finances" }),
  ).toBeVisible();
});
