import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Meals() {
  const [list, setList] = useState(null);
  const [mine, setMine] = useState([]);
  const [ledger, setLedger] = useState(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = async () => {
    const [l, m, lg] = await Promise.all([api('/api/meals'), api('/api/meals/my'), api('/api/meals/ledger/me')]);
    setList(l); setMine(m.rsvps); setLedger(lg);
  };
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const toggle = async (svc) => {
    const next = mine.includes(svc) ? mine.filter((x) => x !== svc) : [...mine, svc];
    try { await api('/api/meals/rsvp', { method: 'POST', body: { services: next } }); await load(); }
    catch (e) { setErr(e.message); await load(); }
  };

  if (!list) return <div>Loading…</div>;

  return (
    <div>
      <h2>Meals</h2>
      <p className="muted">Headcount for the cooks — pick what you'll eat. {list.event.meal_price_per_service_cents > 0 ? `$${(list.event.meal_price_per_service_cents / 100).toFixed(2)}/meal` : 'No charge set yet.'}</p>
      <div className="card">
        {list.services.map((s) => (
          <label key={s.id} className={'meal' + (mine.includes(s.service) ? ' sel' : '')}>
            <input type="checkbox" checked={mine.includes(s.service)} onChange={() => toggle(s.service)} />
            <span>{s.service.replace('_', ' ')}</span>
            <span className="hc">{s.headcount} eating</span>
          </label>
        ))}
      </div>
      {ledger && (
        <div className="card">
          <h3>Your tally</h3>
          <p>Lodging: ${(ledger.lodging_cents / 100).toFixed(2)} · Meals: ${(ledger.meals_cents / 100).toFixed(2)} · <strong>Total: ${(ledger.total_cents / 100).toFixed(2)}</strong></p>
        </div>
      )}
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}
    </div>
  );
}
