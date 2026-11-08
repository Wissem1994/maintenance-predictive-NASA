import { useState } from 'react';
import { FlaskConical, Pause, Play, RotateCcw, Square } from 'lucide-react';
import type { Workspace } from '../hooks/useWorkspace';
import { Badge, date } from './Common';

export function Acquisition({ w }: { w: Workspace }) {
  const [trial, setTrial] = useState('2nd_test');
  const [channel, setChannel] = useState(1);
  const [speed, setSpeed] = useState(60);
  const [tail, setTail] = useState(false);
  const [seed, setSeed] = useState(42);
  const active = ['running', 'paused'].includes(w.engine.status);
  const current = w.datasets?.nasa_ims.trials.find(t => t.trial === trial);
  return <section className="panel acquisition"><div className="section-heading"><div><span className="eyebrow">SOURCE D’ACQUISITION</span><h2>{w.mode === 'nasa' ? 'NASA Replay' : 'Simulation synthétique'}</h2></div><Badge status={w.engine.mode === w.mode ? w.engine.status : 'stopped'}/></div>
    <div className="control-line">{w.mode === 'nasa' ? <>
      <label>Essai expérimental<select value={trial} onChange={e => { setTrial(e.target.value); setChannel(1); }} disabled={active}>{w.datasets?.nasa_ims.trials.map(t => <option key={t.trial} value={t.trial}>{t.trial} · {t.files} fichiers</option>)}</select></label>
      <label>Canal<select value={channel} onChange={e => setChannel(Number(e.target.value))} disabled={active}>{Array.from({ length: current?.channels || 4 }, (_, i) => <option key={i} value={i + 1}>Canal {i + 1}</option>)}</select></label>
      <label>Vitesse<select value={speed} onChange={e => { const s = Number(e.target.value); setSpeed(s); if (active && w.engine.mode === 'nasa') void w.action('/api/replay/speed', { speed: s }); }}>{[1, 10, 60].map(s => <option value={s} key={s}>×{s} · temps historique</option>)}</select></label>
      <label>Point de départ<select value={tail ? 'tail' : 'start'} onChange={e => setTail(e.target.value === 'tail')} disabled={active}><option value="start">Début de l’essai</option><option value="tail">Fin · 30 derniers fichiers</option></select></label>
    </> : <><label>Graine reproductible<input aria-label="Graine du simulateur" type="number" min="0" max="2147483647" value={seed} onChange={e => setSeed(Number(e.target.value))} disabled={active}/></label><div className="synthetic-note"><FlaskConical size={19}/><span>20 équipements fictifs<br/><small>Scénarios physiques simplifiés</small></span></div></>}
      <div className="playback">{!active ? <button className="primary" disabled={w.busy || w.mode === 'nasa' && !current} onClick={() => void w.action(w.mode === 'nasa' ? '/api/replay/start' : '/api/simulation/start', w.mode === 'nasa' ? { trial, channel, speed, start_index: tail ? Math.max(0, (current?.files || 0) - 30) : 0 } : { seed, machine_count: 20 })}><Play size={16}/>Démarrer</button> : <>
        <button disabled={w.busy} onClick={() => void w.action(w.engine.status === 'paused' ? '/api/replay/resume' : '/api/replay/pause')}>{w.engine.status === 'paused' ? <Play size={16}/> : <Pause size={16}/>} {w.engine.status === 'paused' ? 'Reprendre' : 'Pause'}</button>
        <button disabled={w.busy} onClick={() => void w.action('/api/replay/stop')}><Square size={14}/>Arrêter</button></>}
        <button disabled={w.busy || active} title="Réinitialiser la position" aria-label="Réinitialiser la position" onClick={() => void w.action('/api/replay/reset')}><RotateCcw size={16}/></button>
      </div></div>
    {w.engine.mode === 'nasa' && w.engine.total ? <><div className="progress"><span style={{ width: ((w.engine.cursor || 0) / w.engine.total * 100) + '%' }}/></div><div className="control-caption"><span>{w.engine.cursor} / {w.engine.total} fichiers · ×{w.engine.speed}</span><span>Acquisition : {date(w.engine.measured_at)} · Réception : {date(w.engine.received_at)}</span></div></> : <div className="control-caption"><span>{w.mode === 'nasa' ? 'Snapshots à 20 kHz · espacement historique conservé · aucune mesure créée' : 'Données entièrement synthétiques · cycle configuré côté backend'}</span></div>}
    {active && w.engine.mode !== w.mode && <p className="text-amber">Acquisition active dans l’autre mode. Arrêtez-la pour changer de source.</p>}
    {w.engine.error && <p className="text-red">{w.engine.error}</p>}
  </section>;
}
