import { test, expect } from '@playwright/test';

test('actual NASA signal and separate AI4I validation are visible', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Analyse vibratoire', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Signal temporel · A', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Spectre fréquentiel · A', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Modèles IA', exact: true }).click();
  await expect(page.getByText('AI4I 2020 · SYNTHÉTIQUE TABULAIRE · MODÈLE COMPLÉMENTAIRE')).toBeVisible();
  await expect(page.getByText('0,6765', { exact: true })).toBeVisible();
  await page.screenshot({ path: '../docs/reports/model-validation.png', fullPage: true });
});
