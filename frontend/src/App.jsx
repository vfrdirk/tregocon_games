import React, { useEffect, useState, useCallback } from 'react';
import { api } from './api.js';
import Login from './views/Login.jsx';
import Register from './views/Register.jsx';
import Lodging from './views/Lodging.jsx';
import Meals from './views/Meals.jsx';
import Games from './views/Games.jsx';
import Announcements from './views/Announcements.jsx';
import Photos from './views/Photos.jsx';
import Admin from './views/Admin.jsx';
import Privacy from './views/Privacy.jsx';
import Account from './views/Account.jsx';

function fmtDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

function EventBanner({ ev, state }) {
  const start = fmtDate(ev.event_start);
  const end = fmtDate(ev.event_end);
  const regOpen = fmtDate(ev.opens_at);
  const regClose = fmtDate(ev.closes_at);
  return (
    <div className="event-banner">
      <h2>{ev.name}</h2>
      {ev.resort_name && <p className="resort">{ev.resort_name}</p>}
      {start && end && <p className="dates">📅 {start} – {end}</p>}
      {state === 'open' && <p className="open">Registration is open{regClose ? ` until ${regClose}` : ''}.</p>}
      {state === 'before' && regOpen && <p className="soon">Registration opens {regOpen}.</p>}
      {state === 'closed' && <p className="closed">Registration is closed.</p>}
      {state === 'no_event' && <p className="soon">No event scheduled yet.</p>}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('lodging');
  const [accountOpen, setAccountOpen] = useState(false);

  const refreshMe = useCallback(async () => {
    try {
      const me = await api('/api/auth/me');
      setUser(me);
      setView(me.role === 'admin' ? 'dashboard' : 'lodging');
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try { setStatus(await api('/api/event/status')); } catch { setStatus(null); }
  }, []);

  useEffect(() => { refreshMe(); loadStatus(); }, [refreshMe, loadStatus]);

  const logout = async () => { await api('/api/auth/logout', { method: 'POST' }); setUser(null); setView('lodging'); };

  if (loading) return <div className="center">Loading…</div>;

  if (!user) {
    return (
      <div className="authwrap">
        {status && status.event && <EventBanner ev={status.event} state={status.state} />}
        {view === 'privacy' && <Privacy />}
        {view !== 'privacy' && (<><Login onLogin={refreshMe} /><Register /></>)}
        <p className="muted" style={{ textAlign: 'center' }}>
          <a href="#" onClick={(e) => { e.preventDefault(); setView(view === 'privacy' ? 'lodging' : 'privacy'); }}>
            {view === 'privacy' ? 'Back' : 'Privacy Policy'}
          </a>
        </p>
      </div>
    );
  }

  const nav = ['lodging', 'meals', 'games', 'photos', 'announcements'];
  if (user.role === 'admin') nav.push('dashboard');

  return (
    <div className="app">
      <header>
        <h1>TregoCon</h1>
        <nav>
          {nav.map((n) => (
            <button key={n} className={view === n ? 'active' : ''} onClick={() => setView(n)}>
              {n === 'dashboard' ? 'Admin' : n[0].toUpperCase() + n.slice(1)}
            </button>
          ))}
        </nav>
        <div className="who">
          <button className="who-name" onClick={() => setAccountOpen((o) => !o)}>{user.display_name} ▾</button>
          {accountOpen && <Account onLogin={refreshMe} />}
          <button onClick={logout}>Logout</button>
        </div>
      </header>
      <main>
        {view === 'lodging' && <Lodging />}
        {view === 'meals' && <Meals user={user} />}
        {view === 'games' && <Games user={user} />}
        {view === 'announcements' && <Announcements user={user} />}
        {view === 'photos' && <Photos user={user} />}
        {view === 'dashboard' && <Admin user={user} />}
        {view === 'privacy' && <Privacy />}
        <p className="muted" style={{ textAlign: 'center', marginTop: '1rem' }}>
          <a href="#" onClick={(e) => { e.preventDefault(); setView('lodging'); }}>Privacy Policy</a>
        </p>
      </main>
    </div>
  );
}
