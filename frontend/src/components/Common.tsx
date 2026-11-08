import { Activity, ArrowRight, CircleDot } from 'lucide-react';
import type { ReactNode } from 'react';
import type { Workspace } from '../hooks/useWorkspace';

export const labels: Record<string, string> = { running: 'En fonctionnement', stopped: 'À l’arrêt', anomaly: 'Anomalie', paused: 'En pause', completed: 'Terminée', open: 'Ouverte', planned: 'Planifiée', in_progress: 'En cours', error: 'Erreur', warning: 'Avertissement', critical: 'Critique', info: 'Information' };
export const fmt = (v: number | null | undefined, digits = 3) => v == null ? '—' : v.toLocaleString('fr-FR', { maximumFractionDigits: digits, minimumFractionDigits: digits });
export const date = (value?: string | null) => value ? new Date(value).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Aucune mesure';
export function Badge({ status }: { status: string }) { return <span className={'badge ' + status}><i/>{labels[status] || status}</span>; }
export function Empty({ children }: { children: ReactNode }) { return <div className="empty"><CircleDot size={25}/><p>{children}</p></div>; }
export function MachineSelect({ w }: { w: Workspace }) {
  return <select aria-label="Équipement analysé" value={w.selected} onChange={e => w.setSelected(e.target.value)}>{w.machines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select>;
}
export function MachineTable({ w }: { w: Workspace }) {
  return <div className="table-wrap"><table><thead><tr><th>Équipement</th><th>Statut</th><th>Vibration RMS</th><th>Température</th><th>Vitesse</th><th>Score IA</th><th>Dernière acquisition</th><th/></tr></thead>
    <tbody>{w.machines.map(m => <tr key={m.id} onClick={() => { w.setSelected(m.id); w.navigate('machine'); }} tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') { w.setSelected(m.id); w.navigate('machine'); } }}>
      <td><div className="equipment-cell"><div className="machine-icon"><Activity size={18}/></div><div><strong>{m.name}</strong><small>{m.id}</small></div></div></td><td><Badge status={m.status}/></td>
      <td className="mono">{fmt(m.latest?.rms)} <small>{w.mode === 'simulation' ? 'g synth.' : 'u. source'}</small></td>
      <td className="mono">{m.latest?.temperature == null ? '—' : fmt(m.latest.temperature, 1) + ' °C'}</td>
      <td className="mono">{m.latest?.speed_rpm == null ? '—' : fmt(m.latest.speed_rpm, 0) + ' tr/min'}</td>
      <td className={'mono ' + (m.prediction?.is_anomaly ? 'text-amber' : '')}>{fmt(m.prediction?.anomaly_score)}</td>
      <td className="subtle">{date(m.latest?.measured_at)}</td><td><ArrowRight size={16}/></td>
    </tr>)}</tbody></table>{!w.machines.length && <Empty>Aucun équipement. Importez un essai NASA ou démarrez la simulation.</Empty>}</div>;
}
