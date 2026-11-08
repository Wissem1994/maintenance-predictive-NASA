import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { useLive } from './useLive';
import type { Alert, DatasetInfo, EngineState, Machine, Maintenance, Measurement, Mode, Model, Page } from '../types';

export function useWorkspace() {
  const [page, setPage] = useState(location.hash.slice(1) || 'dashboard');
  const [mode, setMode] = useState<Mode>('nasa');
  const [machines, setMachines] = useState<Machine[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [maintenance, setMaintenance] = useState<Maintenance[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [summary, setSummary] = useState<{ machines: number; running: number; stopped: number; anomalies: number; unacknowledged: number; critical_active: number } | null>(null);
  const [datasets, setDatasets] = useState<DatasetInfo | null>(null);
  const [engine, setEngine] = useState<EngineState>({ mode: 'nasa', status: 'stopped' });
  const [selected, setSelected] = useState('');
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [updated, setUpdated] = useState('');
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const [modalMachine, setModalMachine] = useState('');
  const generation = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++generation.current;
    try {
      const [m, a, mt, mo, ds, en, counts] = await Promise.all([
        api<Page<Machine>>('/api/machines?mode=' + mode),
        api<Page<Alert>>('/api/alerts?mode=' + mode + '&limit=200'),
        api<Page<Maintenance>>('/api/maintenance?mode=' + mode + '&limit=200'),
        api<{ items: Model[] }>('/api/models'), api<DatasetInfo>('/api/datasets'), api<EngineState>('/api/engine'), api<NonNullable<typeof summary>>('/api/summary?mode=' + mode),
      ]);
      if (id !== generation.current) return;
      setMachines(m.items); setAlerts(a.items); setMaintenance(mt.items); setModels(mo.items); setDatasets(ds); setEngine(en);
      setSelected(old => m.items.some(item => item.id === old) ? old : m.items[0]?.id || '');
      setSummary(counts); setUpdated(new Date().toISOString()); setError('');
    } catch (e) { if (id === generation.current) setError(e instanceof Error ? e.message : 'Backend indisponible'); }
  }, [mode]);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useEffect(() => {
    setMachines([]); setMeasurements([]); setSelected(''); setSummary(null);
    void refresh();
    const poll = setInterval(() => void refreshRef.current(), 5000);
    return () => { clearInterval(poll); generation.current++; };
  }, [mode, refresh]);
  const connected = useLive(() => void refreshRef.current(), setEngine);
  useEffect(() => {
    if (!selected) return;
    let valid = true;
    const query = new URLSearchParams({ limit: '1000', ...(since ? { since } : {}), ...(until ? { until: until + 'T23:59:59' } : {}) });
    api<Page<Measurement>>('/api/machines/' + selected + '/measurements?' + query)
      .then(data => { if (valid) { setMeasurements(data.items.reverse()); setTotal(data.total); } })
      .catch(e => valid && setError(e.message));
    return () => { valid = false; };
  }, [selected, updated, since, until]);
  async function action(path: string, body?: unknown, method = 'POST') {
    setBusy(true); setError('');
    try { await api(path, method, body); await refreshRef.current(); return true; }
    catch (e) { setError(e instanceof Error ? e.message : 'Action impossible'); return false; }
    finally { setBusy(false); }
  }
  function navigate(next: string) { setPage(next); location.hash = next; }
  const machine = machines.find(m => m.id === selected);
  const activeAlerts = alerts.filter(a => !a.resolved_at);
  const unack = activeAlerts.filter(a => !a.acknowledged_at);
  const activeModels = models.filter(m => m.active && m.metadata_json.provenance.dataset ===
    (mode === 'nasa' ? 'nasa_ims' : 'industrial_simulation'));
  const chartData = measurements.map(m => ({ time: new Date(m.measured_at).toLocaleString('fr-FR',
    { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }), rms: m.rms, score: m.prediction?.anomaly_score }));
  return { page, navigate, mode, setMode, machines, alerts, maintenance, models: activeModels, tabularModels: models.filter(m => m.metadata_json.provenance.dataset === 'ai4i_2020'), datasets, engine,
    selected, setSelected, measurements, total, error, setError, busy, updated, since, setSince, until, setUntil,
    modalMachine, setModalMachine, refresh, action, connected, machine, activeAlerts, unack, chartData, summary };
}
export type Workspace = ReturnType<typeof useWorkspace>;
