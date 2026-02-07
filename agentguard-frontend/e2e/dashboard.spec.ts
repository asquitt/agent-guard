import { expect, test } from '@playwright/test';

test.describe('Dashboard', () => {
  // These tests require a running backend with test data
  // In CI, they would use seeded test data

  test('dashboard page loads for authenticated user', async ({ page }) => {
    // This test would need auth cookies/storage set up
    // Placeholder for when backend is available
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires backend');

    await page.goto('/dashboard');
    await expect(page.getByText(/dashboard|overview/i)).toBeVisible();
  });

  test('incidents page loads', async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires backend');

    await page.goto('/dashboard/incidents');
    await expect(page.getByText(/incidents/i)).toBeVisible();
  });
});
