import { useEffect, useState } from 'react';
import { Bell, Check, CheckCheck, ChevronLeft, ChevronRight, Settings2, Wrench, X } from 'lucide-react';
import { api } from '../services/api';
import type { Alert, Page } from '../types';
import type { Workspace } from '../hooks/useWorkspace';
import { Badge, date, Empty, labels } from '../components/Common';

export function AlertRows({ w, items }: { w: Workspace; items: Alert[] }) {
  if (!items.length) return <Empty>Aucune alerte correspondant aux filtres.</Empty>;
  return <>{items.map(a => <div className="alert-row" key={a.id}><div className={'alert-icon ' + a.severity}><Bell size={17}/></div>
    <div className="grow"><div className="row-title">{a.message}</div><div className="subtle">{a.machine_id} · {date(a.created_at)}</div><details><summary>Mesures déclenchantes</summary><code>{JSON.stringify(a.triggered_values, null, 2)}</code></details></div>
    <span className={'badge ' + (a.resolved_at ? 'completed' : a.severity)}>{a.resolved_at ? 'Résolue' : a.acknowledged_at ? 'Acquittée' : labels[a.severity]}</span>
    {!a.resolved_at && <div className="row-actions">{!a.acknowledged_at && <button disabled={w.busy} onClick={() => void w.action('/api/alerts/' + a.id + '/acknowledge')} title="Acquitter" aria-label={'Acquitter alerte ' + a.id}><Check size={16}/></button>}<button disabled={w.busy} onClick={() => void w.action('/api/alerts/' + a.id + '/resolve')} title="Résoudre" aria-label={'Résoudre alerte ' + a.id}><CheckCheck size={16}/></button><button onClick={() => w.setModalMachine(a.machine_id)} title="Créer une intervention"><Wrench size={16}/></button></div>}
  </div>)}</>;
}

export function Alerts({ w }: { w: Workspace }) {
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<Page<Alert>>({ items: [], total: 0, limit: 20, offset: 0 });
  const [configOpen, setConfigOpen] = useState(false);
  const [threshold, setThreshold] = useState(0.45);
  const [temperature, setTemperature] = useState(80);
  useEffect(() => { setOffset(0); }, [search, severity, status, w.mode]);
  useEffect(() => {
    let valid = true;
    const query = new URLSearchParams({ mode: w.mode, limit: '20', offset: String(offset),
      ...(search ? { search } : {}), ...(severity ? { severity } : {}), ...(status ? { status } : {}) });
    api<Page<Alert>>('/api/alerts?' + query).then(data => valid && setData(data)).catch(e => valid && w.setError(e.message));
    return () => { valid = false; };
  }, [w.mode, w.updated, search, severity, status, offset]);
  return <section className="panel"><div className="section-heading"><div><h2>Journal des alertes</h2><p>{data.total} résultats · persistance, hystérésis et déduplication côté backend</p></div><button onClick={() => setConfigOpen(!configOpen)}><Settings2 size={16}/>Configurer</button></div>
    {configOpen && <form className="config-form" onSubmit={e => { e.preventDefault(); void w.action('/api/alert-config', { vibration_rms: threshold, temperature }, 'PUT'); }}><p>Seuils de démonstration pour la simulation · conservés pendant ce lancement du backend.</p><label>RMS synthétique<input type="number" step="0.01" min="0.01" value={threshold} onChange={e => setThreshold(Number(e.target.value))}/></label><label>Température °C<input type="number" min="26" value={temperature} onChange={e => setTemperature(Number(e.target.value))}/></label><button className="primary" disabled={w.busy}>Appliquer</button></form>}
    <div className="filters alert-filters"><input aria-label="Rechercher des alertes" placeholder="Rechercher dans les messages…" value={search} onChange={e => setSearch(e.target.value)}/><select aria-label="Gravité" value={severity} onChange={e => setSeverity(e.target.value)}><option value="">Toutes les gravités</option><option value="critical">Critiques</option><option value="warning">Avertissements</option><option value="info">Informations</option></select><select aria-label="Statut des alertes" value={status} onChange={e => setStatus(e.target.value)}><option value="">Tous les statuts</option><option value="open">Non acquittées</option><option value="acknowledged">Acquittées</option><option value="resolved">Résolues</option></select></div>
    <AlertRows w={w} items={data.items}/><div className="pagination"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}><ChevronLeft size={15}/>Précédent</button><span>{data.total ? offset + 1 : 0}–{Math.min(offset + 20, data.total)} / {data.total}</span><button disabled={offset + 20 >= data.total} onClick={() => setOffset(offset + 20)}>Suivant<ChevronRight size={15}/></button></div>
  </section>;
}

export function MaintenancePage({ w }: { w: Workspace }) {
  return <><div className="section-heading standalone"><p>{w.maintenance.filter(m => m.status !== 'completed').length} interventions ouvertes ou planifiées</p><button className="primary" disabled={!w.machines.length} onClick={() => w.setModalMachine(w.selected || w.machines[0].id)}><Wrench size={16}/>Nouvelle intervention</button></div>
    <div className="maintenance-grid">{w.maintenance.map(m => <section className="panel maintenance-card" key={m.id}><div className="section-heading"><span className="eyebrow">INT-{String(m.id).padStart(4, '0')} · {m.machine_id}</span><Badge status={m.status}/></div><h2>{m.reason}</h2><p>Priorité : {m.priority} · {m.scheduled_at ? date(m.scheduled_at) : 'Non planifiée'}</p><label>Statut<select value={m.status} onChange={e => void w.action('/api/maintenance/' + m.id, { status: e.target.value, comments: m.comments }, 'PATCH')}>{['open', 'planned', 'in_progress', 'completed'].map(s => <option key={s} value={s}>{labels[s]}</option>)}</select></label>
      <form onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); void w.action('/api/maintenance/' + m.id, { status: m.status, comments: form.get('comment') }, 'PATCH'); }}><label>Commentaires<textarea name="comment" defaultValue={m.comments} key={m.comments} maxLength={4000}/></label><button disabled={w.busy}><Check size={15}/>Enregistrer</button></form></section>)}</div>
    {!w.maintenance.length && <section className="panel"><Empty>Aucune intervention. Créez-en une depuis une alerte ou une fiche équipement.</Empty></section>}
  </>;
}

export function MaintenanceModal({ w }: { w: Workspace }) {
  const [reason, setReason] = useState('');
  const [priority, setPriority] = useState('normal');
  const [scheduled, setScheduled] = useState('');
  const [comments, setComments] = useState('');
  return <div className="modal-backdrop"><form className="modal panel" onSubmit={async e => { e.preventDefault(); const ok = await w.action('/api/maintenance', { machine_id: w.modalMachine, reason, priority, status: scheduled ? 'planned' : 'open', comments, scheduled_at: scheduled || null }); if (ok) w.setModalMachine(''); }}>
    <div className="section-heading"><h2>Nouvelle intervention</h2><button type="button" aria-label="Fermer le formulaire" onClick={() => w.setModalMachine('')}><X size={18}/></button></div><label>Équipement<select required value={w.modalMachine} onChange={e => w.setModalMachine(e.target.value)}>{w.machines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
    <label>Motif<input autoFocus required minLength={3} maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} placeholder="Inspection du roulement…"/></label><label>Priorité<select value={priority} onChange={e => setPriority(e.target.value)}><option value="low">Basse</option><option value="normal">Normale</option><option value="high">Haute</option><option value="critical">Critique</option></select></label><label>Planification<input type="datetime-local" value={scheduled} onChange={e => setScheduled(e.target.value)}/></label><label>Commentaires<textarea maxLength={4000} value={comments} onChange={e => setComments(e.target.value)}/></label><button className="primary" disabled={w.busy}><Check size={16}/>Créer l’intervention</button>
  </form></div>;
}
