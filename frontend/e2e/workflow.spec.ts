import { test, expect } from '@playwright/test';

const API = 'http://127.0.0.1:8000';
test('NASA replay, trained inference, twenty-machine simulation and maintenance', async ({ page, request }) => {
  await request.post(API + '/api/replay/stop');
  await page.goto('/');
  await expect(page.getByText('WebSocket connecté')).toBeVisible();
  await page.getByLabel('Point de départ').selectOption('tail');
  await page.getByRole('button', { name: 'Démarrer', exact: true }).click();
  await expect.poll(async () => (await (await request.get(API + '/api/machines/nasa-2nd_test-ch1/measurements')).json()).total).toBeGreaterThan(0);
  await expect.poll(async () => (await (await request.get(API + '/api/machines/nasa-2nd_test-ch1/predictions')).json()).total).toBeGreaterThan(0);
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reprendre', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Arrêter', exact: true }).click();
  await page.getByRole('button', { name: 'Simulation', exact: true }).click();
  const startedAt = Date.now();
  await page.getByRole('button', { name: 'Démarrer', exact: true }).click();
  await expect(page.getByText('20', { exact: true }).first()).toBeVisible();
  await page.getByRole('row').filter({ hasText: 'R\u00e9ducteur industriel 01' }).click();
  await page.getByLabel('Scénario industriel').selectOption('degradation');
  await expect.poll(async () => {
    const data = await (await request.get(API + '/api/alerts?mode=simulation&machine_id=sim-01&status=open')).json();
    return data.items.filter((a: { created_at: string }) => Date.parse(a.created_at) >= startedAt).length;
  }, { timeout: 80000 }).toBeGreaterThan(0);
  await page.getByRole('button', { name: 'Centre d’alertes', exact: false }).click();
  await page.getByRole('button', { name: /Acquitter alerte/ }).first().click();
  await expect(page.getByText('Acquitt\u00e9e', { exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Maintenance', exact: true }).click();
  await page.getByRole('button', { name: 'Nouvelle intervention' }).click();
  await page.getByLabel('Motif').fill('Inspection démonstration Playwright');
  await page.getByRole('button', { name: 'Créer l’intervention', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Inspection démonstration Playwright' }).first()).toBeVisible();
  await page.getByRole('button', { name: "Vue d'ensemble", exact: true }).click();
  await page.screenshot({ path: '../docs/reports/dashboard-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '../docs/reports/dashboard-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await request.post(API + '/api/replay/stop');
});
