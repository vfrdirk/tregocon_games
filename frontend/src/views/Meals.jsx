import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

const PRETTY = (s) => s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
const money = (c) => `$${(c / 100).toFixed(2)}`;

export default function Meals() {
  const [list, setList] = useState(null);
  const [mine, setMine] = useState([]);
  const [myCompanions, setMyCompanions] = useState([]);
  const [ledger, setLedger] = useState(null);
  const [companion, setCompanion] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = async () => {
    const [l, m, lg] = await Promise.all([api('/api/meals'), api('/api/meals/my'), api('/api/meals/ledger/me')]);
    setList(l); setMine(m.rsvps); setMyCompanions(m.companions || []); setLedger(lg);
  };
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const toggle = async (svc) => {
    const next = mine.includes(svc) ? mine.filter((x) => x !== svc) : [...mine, svc];
    const companions = companion.trim() ? [companion.trim()] : myCompanions;
    try { await api('/api/meals/rsvp', { method: 'POST', body: { services: next, companions } }); await load(); }
    catch (e) { setErr(e.message); await load(); }
  };

  if (!list) return <div>Loading…</div>;
  const price = list.event.meal_price_per_service_cents;

  return (
    <div>
      <h2>Meals</h2>
      <p className="muted">Headcount for the cooks — pick what you'll eat. {price > 0 ? `${money(price)}/meal` : 'No charge set yet.'}</p>
      <div className="card">
        <div className="mealrow head">
          <span className="mk"></span>
          <span className="mname">Meal</span>
          <span className="mhc">Eating</span>
        </div>
        {list.services.map((s) => (
          <label key={s.id} className={'mealrow' + (mine.includes(s.service) ? ' sel' : '')}>
            <span className="mk"><input type="checkbox" checked={mine.includes(s.service)} onChange={() => toggle(s.service)} /></span>
            <span className="mname">{s.label}</span>
            <span className="mhc">{s.headcount}</span>
          </label>
        ))}
        <div className="companion-box">
          <label>Add companion (spouse/child) to your meals
            <input placeholder="Full name" value={companion} onChange={(e) => setCompanion(e.target.value)} />
          </label>
          {myCompanions.length > 0 && <p className="muted">Registered companions: {myCompanions.join(', ')}</p>}
          <p className="muted">Companion eats the same meals you select. Saved when you toggle any meal.</p>
        </div>
      </div>
      <div className="card">
        <h3>Who's bringing what</h3>
        {list.services.map((s) => (
          <div key={s.id} className="mealvol">
            <strong>{s.label}</strong>
            {s.volunteers && s.volunteers.length > 0 ? (
              <ul>{s.volunteers.map((v, i) => <li key={i}>{v.name}{v.dish ? ` — ${v.dish}` : ''}</li>)}</ul>
            ) : <p className="muted">No dishes signed up yet.</p>}
          </div>
        ))}
      </div>
      {ledger && (
        <div className="card">
          <h3>Your tally</h3>
          <p>Lodging: {money(ledger.lodging_cents)} · Meals: {money(ledger.meals_cents)} · <strong>Total: {money(ledger.total_cents)}</strong></p>
        </div>
      )}
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}
    </div>
  );
}
