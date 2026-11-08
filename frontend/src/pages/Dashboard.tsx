import { Activity, ArrowRight, Bell, Gauge, ShieldCheck, Waves } from 'lucide-react';
import type { Workspace } from '../hooks/useWorkspace';
import { Acquisition } from '../components/Acquisition';
import { Empty, fmt, MachineSelect, MachineTable } from '../components/Common';
import { Trend } from '../components/Trend';

export function Dashboard({ w }: { w: Workspace }) {
  const kpis = [
    { label: 'Équipements suivis', value: w.summary?.machines ?? w.machines.length, caption: 'Sources distinctes et traçables', icon: Activity, color: 'green' },
    { label: 'En fonctionnement', value: w.summary?.running ?? w.machines.filter(m => ['running', 'anomaly'].includes(m.status)).length, caption: (w.summary?.stopped ?? w.machines.filter(m => m.status === 'stopped').length) + ' à l’arrêt', icon: Gauge, color: 'green' },
    { label: 'Équipements en anomalie', value: w.summary?.anomalies ?? w.machines.filter(m => m.status === 'anomaly').length, caption: 'Dernière inférence disponible', icon: Waves, color: 'amber' },
    { label: 'Alertes non acquittées', value: w.summary?.unacknowledged ?? w.unack.length, caption: (w.summary?.critical_active ?? w.activeAlerts.filter(a => a.severity === 'critical').length) + ' alertes critiques actives', icon: Bell, color: 'red' },
  ];
  return <><Acquisition w={w}/><div className="kpi-grid">{kpis.map(k => <section className="panel kpi" key={k.label}><div className="kpi-label">{k.label}<span className={'kpi-icon ' + k.color}><k.icon size={18}/></span></div><strong>{String(k.value).padStart(2, '0')}</strong><small>{k.caption}</small></section>)}</div>
    <div className="dashboard-grid"><section className="panel"><div className="section-heading"><div><h2>Tendance vibratoire</h2><p>RMS · {w.mode === 'nasa' ? 'unité source non vérifiée' : 'g synthétique'}</p></div><MachineSelect w={w}/></div><Trend data={w.chartData} x="time" y="rms"/><div className="chart-footer"><span className="legend-dot"/> Horodatages de mesure · {w.measurements.length} points persistés</div></section>
    <section className="panel attention"><div className="section-heading"><div><h2>À votre attention</h2><p>Équipements à examiner</p></div><span className="count">{w.machines.filter(m => m.prediction?.is_anomaly).length}</span></div>{w.machines.filter(m => m.prediction?.is_anomaly).sort((a, b) => (b.prediction?.baseline_z || 0) - (a.prediction?.baseline_z || 0)).slice(0, 4).map(m => <button className="attention-item" key={m.id} onClick={() => { w.setSelected(m.id); w.navigate('machine'); }}><div className="alert-icon warning"><Waves size={17}/></div><div><strong>{m.name}</strong><small>Score {fmt(m.prediction?.anomaly_score)} · z {fmt(m.prediction?.baseline_z, 1)}</small></div><ArrowRight size={15}/></button>)}{!w.machines.some(m => m.prediction?.is_anomaly) && <Empty>Aucune anomalie dans les dernières inférences.</Empty>}<div className="science-note"><ShieldCheck size={16}/><p>Le score décrit un écart aux données de référence. Il ne constitue pas une probabilité de panne.</p></div></section></div>
    <section className="panel"><div className="section-heading"><div><h2>Parc d’équipements</h2><p>{w.machines.length} équipements · {w.mode === 'nasa' ? 'NASA Replay' : 'Simulation synthétique'}</p></div><button className="text-button" onClick={() => w.navigate('live')}>Superviser le parc <ArrowRight size={15}/></button></div><MachineTable w={w}/></section></>;
}
