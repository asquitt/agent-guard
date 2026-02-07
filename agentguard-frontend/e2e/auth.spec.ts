import { expect, test } from '@playwright/test';

test.describe('Authentication', () => {
  test('login page renders correctly', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /sign in|log in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in|log in/i })).toBeVisible();
  });

  test('register page renders correctly', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByLabel(/name/i).first()).toBeVisible();
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('wrong@example.com');
    await page.getByLabel(/password/i).fill('WrongPassword1!');
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    // Should show some error indication
    await expect(page.getByText(/invalid|error|failed/i)).toBeVisible({ timeout: 5000 });
  });

  test('unauthenticated user redirected to login', async ({ page }) => {
    await page.goto('/dashboard');
    // ProtectedRoute should redirect to /login
    await page.waitForURL(/\/login/);
    await expect(page).toHaveURL(/\/login/);
  });
});
