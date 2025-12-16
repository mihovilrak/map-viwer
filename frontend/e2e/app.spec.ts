import {expect, test} from "@playwright/test";

test.describe("App E2E", () => {
  test("loads home page", async ({page, baseURL}) => {
    test.skip(!baseURL, "baseURL not configured");
    await page.goto("/");
    await expect(page.getByText(/Map Viewer/i)).toBeVisible();
  });
});

