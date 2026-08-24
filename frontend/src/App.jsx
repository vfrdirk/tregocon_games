import React, { useEffect, useState, useCallback } from 'react';
import { api } from './api.js';
import Login from './views/Login.jsx';
import Register from './views/Register.jsx';
import Lodging from './views/Lodging.jsx';
import Meals from './views/Meals.jsx';
import Games from './views/Games.jsx';
import Announcements from './views/Announcements.jsx';
import Admin from './views/Admin.jsx';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('lodging');

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

  useEffect(() => { refreshMe(); }, [refreshMe]);

  const logout = async () => { await api('/api/auth/logout', { method: 'POST' }); setUser(null); setView('lodging'); };

  if (loading) return <div className="center">Loading…</div>;

  if (!user) {
    return (
      <div className="authwrap">
        <Login onLogin={refreshMe} />
        <Register />
      </div>
    );
  }

  const nav = ['lodging', 'meals', 'games', 'announcements'];
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
          <span>{user.display_name}</span>
          <button onClick={logout}>Logout</button>
        </div>
      </header>
      <main>
        {view === 'lodging' && <Lodging user={user} />}
        {view === 'meals' && <Meals user={user} />}
        {view === 'games' && <Games user={user} />}
        {view === 'announcements' && <Announcements user={user} />}
        {view === 'dashboard' && <Admin user={user} />}
      </main>
    </div>
  );
}
