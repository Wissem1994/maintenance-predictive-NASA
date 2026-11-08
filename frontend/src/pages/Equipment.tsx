import { useEffect, useState } from 'react';
import { Activity, ArrowDownToLine, ArrowRight, Wrench } from 'lucide-react';
import type { Workspace } from '../hooks/useWorkspace';
import { api } from '../services/api';
import type { Signal } from '../types';
import { Badge, date, Empty, fmt, MachineSelect } from '../components/Common';
import { Trend } from '../components/Trend';
import { AlertRows } from './Operations';

const scenarios = { normal: 'Fonctionnement normal', degradation: 'Dégradation progressive', overheating: 'Échauffement anormal', imbalance: 'Déséquilibre', bearing: 'Dégradation du roulement', vibration: 'Vibrations croissantes', shutdown: 'Arrêt de la machine', maintenance: 'Maintenance corrective', recovery: 'Retour à la normale' };

export function Equipment({ w }: { w: Workspace }) {
  const machine = w.machine;
  if (!machine) return <Empty>Sélectionnez un équipement dans la supervision.</Empty>;
  const latest = w.measurements.at(-1);
  function download() {
    const rows = ['measured_at,received_at,provenance,rms,anomaly_score', ...w.measurements.map(m =>
      [m.measured_at, m.received_at, m.provenance, m.rms, m.prediction?.anomaly_score ?? ''].join(','))];
    const url = URL.createObjectURL(new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = w.selected + '-measurements.csv'; link.click(); URL.revokeObjectURL(url);
  }
  return <>
    <section className="panel machine-heading"><div className="machine-icon large"><Activity size={27}/></div><div className="grow"><div className="eyebrow">{machine.id}</div><h2>{machine.name}</h2><p>{machine.equipment_type} · {machine.metadata_json.unit}</p></div><Badge status={machine.status}/><span className="subtle">Risque : {machine.prediction?.risk || 'indisponible'}</span><button onClick={() => w.setModalMachine(w.selected)}><Wrench size={16}/>Créer une intervention</button></section>
    {w.mode === 'simulation' && <section className="panel scenario-control"><label>Scénario industriel<select aria-label="Scénario industriel" disabled={w.busy || w.engine.mode !== 'simulation' || !['running','paused'].includes(w.engine.status)} defaultValue="normal" key={w.selected} onChange={e => void w.action('/api/simulation/' + w.selected + '/scenario', { scenario: e.target.value })}>{Object.entries(scenarios).map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></label><p>Progression reproductible par cycle ; hypothèses physiques simplifiées.</p></section>}
    <section className="panel"><div className="section-heading"><div><h2>Historique des mesures</h2><p>{w.total} mesures correspondant au filtre · {w.measurements.length} affichées</p></div><div className="filters"><label>Du<input type="date" value={w.since} onChange={e => w.setSince(e.target.value)}/></label><label>Au<input type="date" value={w.until} onChange={e => w.setUntil(e.target.value)}/></label><button onClick={download} disabled={!w.measurements.length}><ArrowDownToLine size={15}/>CSV</button></div></div><Trend data={w.chartData} x="time" y="rms"/></section>
    <div className="dashboard-grid"><section className="panel"><div className="section-heading"><div><h2>Score d’anomalie</h2><p>{machine.prediction?.model_version || 'Aucun modèle compatible chargé'}</p></div></div><Trend data={w.chartData} x="time" y="score" color="#e0b671"/><div className="chart-footer">Seuil du modèle : {fmt(machine.prediction?.threshold)} · probabilité de panne : indisponible</div></section>
    <section className="panel"><div className="section-heading"><h2>Caractéristiques vibratoires</h2><button onClick={() => w.navigate('analysis')}>Analyser<ArrowRight size={14}/></button></div><div className="feature-grid">{['rms', 'kurtosis', 'crest_factor', 'skewness', 'std', 'dominant_frequency_1'].map(k => <div key={k}><span>{k.replaceAll('_', ' ')}</span><strong>{fmt(latest?.features?.[k])}</strong></div>)}</div><p className="panel-note">Mesure : {date(latest?.measured_at)}<br/>Réception : {date(latest?.received_at)}</p></section></div>
    <section className="panel"><div className="section-heading"><h2>Alertes de l’équipement</h2></div><AlertRows w={w} items={w.alerts.filter(a => a.machine_id === w.selected)}/></section>
    <section className="panel"><div className="section-heading"><h2>Interventions</h2></div>{w.maintenance.filter(m => m.machine_id === w.selected).map(m => <div className="maintenance-summary" key={m.id}><Wrench size={17}/><strong>{m.reason}</strong><Badge status={m.status}/><span>{m.comments}</span></div>)}{!w.maintenance.some(m => m.machine_id === w.selected) && <Empty>Aucune intervention.</Empty>}</section>
  </>;
}

export function Analysis({ w }: { w: Workspace }) {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [comparison, setComparison] = useState<Signal | null>(null);
  const [signalId, setSignalId] = useState('');
  const [compareId, setCompareId] = useState('');
  useEffect(() => { setSignalId(''); setCompareId(''); setSignal(null); setComparison(null); }, [w.selected]);
  useEffect(() => {
    if (!w.selected || !w.measurements.length) { setSignal(null); return; }
    let valid = true;
    api<Signal>('/api/machines/' + w.selected + '/signal' + (signalId ? '?measurement_id=' + signalId : ''))
      .then(data => valid && setSignal(data)).catch(e => valid && w.setError(e.message));
    return () => { valid = false; };
  }, [w.selected, signalId, w.updated, w.measurements.length]);
  useEffect(() => {
    if (!w.selected || !compareId) { setComparison(null); return; }
    let valid = true;
    api<Signal>('/api/machines/' + w.selected + '/signal?measurement_id=' + compareId)
      .then(data => valid && setComparison(data)).catch(e => valid && w.setError(e.message));
    return () => { valid = false; };
  }, [w.selected, compareId]);
  const options = w.measurements.slice().reverse().map(m => <option key={m.id} value={m.id}>{date(m.measured_at)} · #{m.id}</option>);
  return <>
    <section className="panel"><div className="section-heading"><div><h2>Exploration du signal</h2><p>Signal brut à la demande · aperçu réduit avec conservation des extrema</p></div><MachineSelect w={w}/></div><div className="filters analysis-filters"><label>Mesure A<select value={signalId} onChange={e => setSignalId(e.target.value)}><option value="">Dernière mesure</option>{options}</select></label><label>Comparer à B<select value={compareId} onChange={e => setCompareId(e.target.value)}><option value="">Aucune comparaison</option>{options}</select></label></div></section>
    {signal ? <><div className="feature-strip">{['rms', 'kurtosis', 'crest_factor', 'peak_to_peak'].map(k => <section className="panel" key={k}><span className="subtle">{k.replaceAll('_', ' ')}</span><strong>{fmt(signal.features[k])}</strong><small>{comparison ? 'B : ' + fmt(comparison.features[k]) : date(signal.measured_at)}</small></section>)}</div>
      <section className="panel"><div className="section-heading"><div><h2>Signal temporel · A</h2><p>{signal.sample_count.toLocaleString('fr-FR')} points · {signal.sample_rate_hz.toLocaleString('fr-FR')} Hz · {fmt(signal.sample_count / signal.sample_rate_hz)} s · amplitude source</p></div></div><Trend data={signal.signal} x="time" y="value" area={false}/></section>
      <section className="panel"><div className="section-heading"><div><h2>Spectre fréquentiel · A</h2><p>FFT unilatérale · fenêtre Hann · moyenne retirée · amplitude crête</p></div></div><Trend data={signal.spectrum} x="frequency" y="amplitude" color="#87b9e8" area={false}/></section>
      {comparison && <section className="panel"><div className="section-heading"><h2>Spectre de comparaison · B — {date(comparison.measured_at)}</h2></div><Trend data={comparison.spectrum} x="frequency" y="amplitude" color="#e0b671" area={false}/></section>}
    </> : <Empty>Démarrez une acquisition pour analyser un signal réel ou synthétique.</Empty>}
  </>;
}
