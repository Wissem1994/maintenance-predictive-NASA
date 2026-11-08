import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

const calls: string[] = [];
beforeEach(() => {
  calls.length = 0;
  location.hash = '';
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
  vi.stubGlobal('WebSocket', class { onopen = null; onmessage = null; onclose = null; close() {} });
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    calls.push(url);
    const value = url.includes('/datasets') ? { nasa_ims: { available: false, trials: [], sample_rate_hz: 20000 } }
      : url.includes('/engine') ? { mode: 'nasa', status: 'stopped' } : { items: [], total: 0, limit: 20, offset: 0 };
    return { ok: true, json: async () => value };
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe('Connected workspace', () => {
  it('shows honest empty data and disables NASA replay without files', async () => {
    render(<App/>);
    await waitFor(() => expect(calls.some(c => c.includes('/datasets'))).toBe(true));
    expect(screen.getByText(/Données expérimentales historiques/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Démarrer' })).toBeDisabled();
    expect(screen.getAllByText('00')).toHaveLength(4);
  });
  it('requests separate simulation data when changing mode', async () => {
    render(<App/>);
    fireEvent.click(screen.getByRole('button', { name: 'Simulation' }));
    await waitFor(() => expect(calls.some(c => c.includes('/machines?mode=simulation'))).toBe(true));
    expect(screen.getByText(/Données synthétiques · équipements fictifs/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Démarrer' })).toBeEnabled();
  });
  it('opens the model page without inventing model metrics', async () => {
    render(<App/>);
    fireEvent.click(screen.getByRole('button', { name: 'Modèles IA' }));
    await screen.findByText(/Aucun modèle compatible entraîné/);
    expect(screen.getByText(/La proportion d’anomalies ne mesure pas/)).toBeInTheDocument();
  });
});
