import { useEffect, useRef, useState } from 'react';
import { Activity, Bell, Box, ChevronRight, Database, FlaskConical, LayoutDashboard, Moon, Radio, ShieldCheck, Sun, Volume2, VolumeX, Waves, Wrench, X } from 'lucide-react';
import { useWorkspace } from './hooks/useWorkspace';
import { date, MachineTable } from './components/Common';
import { Acquisition } from './components/Acquisition';
import { Dashboard } from './pages/Dashboard';
import { Analysis, Equipment } from './pages/Equipment';
import { Alerts, MaintenanceModal, MaintenancePage } from './pages/Operations';
import { DataPage, Models } from './pages/Science';

const nav = [
  ['dashboard', "Vue d'ensemble", LayoutDashboard], ['live', 'Supervision en direct', Radio],
  ['analysis', 'Analyse vibratoire', Waves], ['alerts', "Centre d’alertes", Bell],
  ['maintenance', 'Maintenance', Wrench], ['models', 'Modèles IA', Box], ['data', 'Données & traçabilité', Database],
] as const;

export default function App() {
  const w = useWorkspace();
  const [light, setLight] = useState(false);
  const [sound, setSound] = useState(false);
  const audio = useRef<AudioContext | null>(null);
  const lastAlert = useRef(0);
  useEffect(() => { document.documentElement.dataset.theme = light ? 'light' : 'dark'; }, [light]);
  useEffect(() => {
    const latest = Math.max(0, ...w.alerts.map(a => a.id));
    if (sound && lastAlert.current && latest > lastAlert.current && audio.current) {
      const oscillator = audio.current.createOscillator(), gain = audio.current.createGain();
      oscillator.connect(gain); gain.connect(audio.current.destination); oscillator.frequency.value = 660;
      gain.gain.setValueAtTime(0.06, audio.current.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audio.current.currentTime + 0.35);
      oscillator.start(); oscillator.stop(audio.current.currentTime + 0.35);
    }
    lastAlert.current = latest;
  }, [w.alerts, sound]);
  const title = w.page === 'machine' ? 'Fiche équipement' : nav.find(n => n[0] === w.page)?.[1] || "Vue d’ensemble";
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#dashboard" onClick={() => w.navigate('dashboard')}><div className="brand-mark"><Activity size={24}/></div><span>PredictMaint <b>AI</b><small>INDUSTRIAL INTELLIGENCE</small></span></a>
      <div className="workspace"><div className="workspace-icon">P</div><div>Laboratoire de supervision<small>Projet d’ingénierie · local</small></div><ShieldCheck size={15}/></div>
      <span className="nav-label">ESPACE DE TRAVAIL</span><nav>{nav.map(([id, name, Icon]) => <button key={id} className={w.page === id || w.page === 'machine' && id === 'live' ? 'active' : ''} onClick={() => w.navigate(id)}><Icon size={18}/>{name}{id === 'alerts' && (w.summary?.unacknowledged ?? w.unack.length) > 0 && <em>{w.summary?.unacknowledged ?? w.unack.length}</em>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-status"><i/> Environnement local<span>v0.1.0</span></div><p>Prototype de recherche<br/>Seuils non validés industriellement</p><button className="theme-button" onClick={() => setLight(!light)}>{light ? <Moon size={16}/> : <Sun size={16}/>} {light ? 'Thème sombre' : 'Thème clair'}</button></div>
    </aside>
    <main><header className="topbar"><div className="breadcrumbs">Plateforme<ChevronRight size={13}/><strong>{title}</strong></div><div className="top-actions"><span className={'connection ' + (w.connected ? 'online' : '')}><i/>{w.connected ? 'WebSocket connecté' : 'Reconnexion…'}</span><button aria-label="Notifications sonores" title="Notifications sonores" className={sound ? 'sound-on' : ''} onClick={() => { if (!sound) { audio.current ||= new AudioContext(); void audio.current.resume(); } setSound(!sound); }}>{sound ? <Volume2 size={18}/> : <VolumeX size={18}/>}</button><button aria-label="Ouvrir les alertes" onClick={() => w.navigate('alerts')}><Bell size={18}/>{(w.summary?.unacknowledged ?? w.unack.length) > 0 && <i className="notification-dot"/>}</button><span className="avatar">PM</span></div></header>
      <div className="content"><div className="page-heading"><div><div className="eyebrow"><span className="green-dot"/>CONDITION MONITORING</div><h1>{title}</h1><p>Observer les signaux. Comprendre les anomalies. Préparer l’intervention.</p></div><div className="mode-switch"><button className={w.mode === 'nasa' ? 'selected' : ''} onClick={() => w.setMode('nasa')}><Database size={15}/>NASA Replay</button><button className={w.mode === 'simulation' ? 'selected' : ''} onClick={() => w.setMode('simulation')}><FlaskConical size={15}/>Simulation</button></div></div>
        <div className={'source-banner ' + w.mode}><div><span className="source-label">{w.mode === 'nasa' ? 'NASA Replay' : 'Simulation synthétique'}</span><span>{w.mode === 'nasa' ? 'Données expérimentales historiques · NASA IMS / University of Cincinnati' : 'Données synthétiques · équipements fictifs · aucune mesure NASA'}</span></div><span>Actualisation : {w.updated ? date(w.updated) : 'connexion…'}</span></div>
        {w.error && <div className="error-banner" role="alert">{w.error}<button aria-label="Fermer l’erreur" onClick={() => w.setError('')}><X size={16}/></button></div>}
        {w.page === 'dashboard' && <Dashboard w={w}/>}
        {w.page === 'live' && <><Acquisition w={w}/><section className="panel"><div className="section-heading"><div><h2>Mesures en direct</h2><p>Réception WebSocket · mesures persistées après chaque acquisition</p></div><span className="live-indicator"><i/>LIVE</span></div><MachineTable w={w}/></section></>}
        {w.page === 'machine' && <Equipment w={w}/>}
        {w.page === 'analysis' && <Analysis w={w}/>}
        {w.page === 'alerts' && <Alerts w={w}/>}
        {w.page === 'maintenance' && <MaintenancePage w={w}/>}
        {w.page === 'models' && <Models w={w}/>}
        {w.page === 'data' && <DataPage w={w}/>}
        <footer className="content-footer"><span>PredictMaint AI · Ingénierie de maintenance prédictive</span><span>NASA IMS + simulation traçable · Recherche & démonstration</span></footer>
      </div></main>{w.modalMachine && <MaintenanceModal w={w}/>}
  </div>;
}
