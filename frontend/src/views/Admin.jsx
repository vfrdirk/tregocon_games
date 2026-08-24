import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Admin() {
  const [tab, setTab] = useState('dashboard');
  const [dash, setDash] = useState(null);
  const [users, setUsers] = useState([]);
  const [comms, setComms] = useState(null);
  const [cfg, setCfg] = useState({ lodging_rate_per_night_cents: 5000, meal_price_per_service_cents: 0 });
  const [nextYear, setNextYear] = useState(new Date().getFullYear() + 1);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const loadDash = async () => { try { setDash((await api('/api/admin/dashboard')).lodging); } catch (e) { setErr(e.message); } };
  const loadUsers = async () => { try { setUsers((await api('/api/admin/users')).users); } catch (e) { setErr(e.message); } };
  const loadComms = async () => { try { setComms(await api('/api/admin/event/comms-status')); } catch (e) { setErr(e.message); } };

  useEffect(() => {
    if (tab === 'dashboard') loadDash();
    if (tab === 'users') loadUsers();
    if (tab === 'comms') loadComms();
  }, [tab]);

  const setStatus = async (id, status) => { try { await api(`/api/admin/users/${id}`, { method: 'POST', body: { status } }); await loadUsers(); } catch (e) { setErr(e.message); } };
  const saveCfg = async (e) => { e.preventDefault(); try { await api('/api/admin/event/config', { method: 'PUT', body: cfg }); setMsg('Config saved'); } catch (e) { setErr(e.message); } };
  const createNext = async () => {
    try { const r = await api('/api/admin/event/create-next', { method: 'POST', body: { year: nextYear } }); setMsg(r.message); }
    catch (e) { setErr(e.message); }
  };

  return (
    <div>
      <h2>Admin</h2>
      <nav className="subnav">
        {['dashboard', 'users', 'config', 'comms'].map((t) => <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>)}
      </nav>
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}

      {tab === 'dashboard' && dash && (
        <div className="card">
          <h3>Coordinator summary</h3>
          <p>Reservations: {dash.reservations} · Rooms filled: {dash.rooms_filled}/{dash.rooms_total} · Nights booked: {dash.nights_booked}</p>
          <p>Lodging revenue: ${(dash.lodging_revenue_cents / 100).toFixed(2)} · Paid: {dash.paid_count}</p>
        </div>
      )}

      {tab === 'users' && (
        <div className="card">
          <h3>Users</h3>
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Set</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.display_name}</td><td>{u.email}</td><td>{u.status}</td>
                  <td>
                    {['approved', 'admin', 'pending'].map((s) => <button key={s} onClick={() => setStatus(u.id, s)}>{s}</button>)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'config' && (
        <div className="card">
          <h3>Event settings</h3>
          <form onSubmit={saveCfg}>
            <label>Lodging $/night (cents)<input type="number" value={cfg.lodging_rate_per_night_cents} onChange={(e) => setCfg({ ...cfg, lodging_rate_per_night_cents: +e.target.value })} /></label>
            <label>Meal $/service (cents)<input type="number" value={cfg.meal_price_per_service_cents} onChange={(e) => setCfg({ ...cfg, meal_price_per_service_cents: +e.target.value })} /></label>
            <button type="submit">Save</button>
          </form>
          <h3>Next event</h3>
          <label>Year<input type="number" value={nextYear} onChange={(e) => setNextYear(+e.target.value)} /></label>
          <button onClick={createNext}>Create next event (copy template)</button>
        </div>
      )}

      {tab === 'comms' && comms && (
        <div className="card">
          <h3>Comms channels</h3>
          <p>Email (SES): <strong>{comms.email_enabled ? 'LIVE' : 'disabled (no AWS creds)'}</strong></p>
          <p>SMS (Twilio): <strong>{comms.sms_enabled ? 'LIVE' : 'disabled (no Twilio creds)'}</strong></p>
        </div>
      )}
    </div>
  );
}
