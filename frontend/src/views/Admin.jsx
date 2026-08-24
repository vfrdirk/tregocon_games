import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Admin() {
  const [tab, setTab] = useState('dashboard');
  const [dash, setDash] = useState(null);
  const [users, setUsers] = useState([]);
  const [comms, setComms] = useState(null);
  const [cfg, setCfg] = useState({ name: '', resort_name: '', opens_at: '', closes_at: '', lodging_rate_per_night_cents: 5000, meal_price_per_service_cents: 0 });

  const loadCfg = async () => {
    try {
      const r = await api('/api/event/config');
      if (r.event) {
        const e = r.event;
        setCfg({
          name: e.name || '',
          resort_name: e.resort_name || '',
          opens_at: e.opens_at ? e.opens_at.slice(0, 16) : '',
          closes_at: e.closes_at ? e.closes_at.slice(0, 16) : '',
          lodging_rate_per_night_cents: e.lodging_rate_per_night_cents ?? 5000,
          meal_price_per_service_cents: e.meal_price_per_service_cents ?? 0,
        });
      }
    } catch (e) { setErr(e.message); }
  };
  const [nextYear, setNextYear] = useState(new Date().getFullYear() + 1);
  const [rooms, setRooms] = useState([]);
  const [roomEdits, setRoomEdits] = useState({});
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const loadDash = async () => {
    try {
      const r = await api('/api/admin/dashboard');
      setDash(r.event ? r.lodging : null);
      if (!r.event) setMsg('No event yet — seed the first event (run the seed script or use "Create next event" after one exists).');
    } catch (e) { setErr(e.message); }
  };
  const loadUsers = async () => { try { setUsers((await api('/api/admin/users')).users); } catch (e) { setErr(e.message); } };
  const loadComms = async () => { try { setComms(await api('/api/admin/event/comms-status')); } catch (e) { setErr(e.message); } };
  const loadRooms = async () => {
    try {
      const d = await api('/api/lodging/availability');
      const flat = [];
      for (const lg of (d.lodges || [])) for (const r of lg.rooms) flat.push(r);
      setRooms(flat);
      const init = {};
      for (const r of flat) init[r.id] = { label: r.label, floor: r.floor, bed_config: r.bed_config };
      setRoomEdits(init);
      if (!d.lodges || d.lodges.length === 0) setMsg('No rooms yet — seed an event first.');
    } catch (e) { setErr(e.message); }
  };

  useEffect(() => {
    if (tab === 'dashboard') loadDash();
    if (tab === 'users') loadUsers();
    if (tab === 'comms') loadComms();
    if (tab === 'rooms') loadRooms();
    if (tab === 'config') loadCfg();
  }, [tab]);

  const setStatus = async (id, status) => { try { await api(`/api/admin/users/${id}`, { method: 'POST', body: { status } }); await loadUsers(); } catch (e) { setErr(e.message); } };
  const saveCfg = async (e) => {
    e.preventDefault();
    const body = {
      ...cfg,
      registration_opens_at: cfg.opens_at || null,
      registration_closes_at: cfg.closes_at || null,
    };
    delete body.opens_at;
    delete body.closes_at;
    try { await api('/api/admin/event/config', { method: 'PUT', body }); setMsg('Config saved'); }
    catch (e) { setErr(e.message); }
  };
  const createNext = async () => {
    try { const r = await api('/api/admin/event/create-next', { method: 'POST', body: { year: nextYear } }); setMsg(r.message); }
    catch (e) { setErr(e.message); }
  };
  const saveRoom = async (id) => {
    try {
      const e = roomEdits[id];
      await api(`/api/admin/room/${id}`, { method: 'PATCH', body: e });
      setMsg(`Saved "${e.label}"`);
      await loadRooms();
    } catch (er) { setErr(er.message); }
  };

  return (
    <div>
      <h2>Admin</h2>
      <nav className="subnav">
        {['dashboard', 'users', 'rooms', 'config', 'comms'].map((t) => <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>)}
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
                    <select id={`ustat-${u.id}`} defaultValue={u.status}>
                      <option value="pending">Pending</option>
                      <option value="approved">Approved</option>
                      <option value="admin">Admin</option>
                    </select>
                    <button onClick={() => setStatus(u.id, document.getElementById(`ustat-${u.id}`).value)}>Set</button>
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
            <label>Event name<input type="text" value={cfg.name} onChange={(e) => setCfg({ ...cfg, name: e.target.value })} /></label>
            <label>Resort / venue name<input type="text" value={cfg.resort_name} onChange={(e) => setCfg({ ...cfg, resort_name: e.target.value })} /></label>
            <label>Registration opens<input type="datetime-local" value={cfg.opens_at} onChange={(e) => setCfg({ ...cfg, opens_at: e.target.value })} /></label>
            <label>Registration closes<input type="datetime-local" value={cfg.closes_at} onChange={(e) => setCfg({ ...cfg, closes_at: e.target.value })} /></label>
            <label>Lodging $/night (cents)<input type="number" value={cfg.lodging_rate_per_night_cents} onChange={(e) => setCfg({ ...cfg, lodging_rate_per_night_cents: +e.target.value })} /></label>
            <label>Meal $/service (cents)<input type="number" value={cfg.meal_price_per_service_cents} onChange={(e) => setCfg({ ...cfg, meal_price_per_service_cents: +e.target.value })} /></label>
            <button type="submit">Save</button>
          </form>
          <h3>Next event</h3>
          <label>Year<input type="number" value={nextYear} onChange={(e) => setNextYear(+e.target.value)} /></label>
          <button onClick={createNext}>Create next event (copy template)</button>
        </div>
      )}

      {tab === 'rooms' && (
        <div className="card">
          <h3>Rooms (rename / relabel live)</h3>
          <p className="muted">Edit a room's name or floor and Save. No redeploy needed.</p>
          {rooms.map((r) => (
            <div key={r.id} className="roomedit">
              <input value={roomEdits[r.id]?.label || ''} onChange={(e) => setRoomEdits({ ...roomEdits, [r.id]: { ...roomEdits[r.id], label: e.target.value } })} />
              <select value={roomEdits[r.id]?.floor || 'main'} onChange={(e) => setRoomEdits({ ...roomEdits, [r.id]: { ...roomEdits[r.id], floor: e.target.value } })}>
                <option value="upstairs">Upstairs</option>
                <option value="main">Main</option>
                <option value="down">Down</option>
              </select>
              <select value={roomEdits[r.id]?.bed_config || 'double'} onChange={(e) => setRoomEdits({ ...roomEdits, [r.id]: { ...roomEdits[r.id], bed_config: e.target.value } })}>
                <option value="double">2 beds</option>
                <option value="single">Queen</option>
              </select>
              <button onClick={() => saveRoom(r.id)}>Save</button>
            </div>
          ))}
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
