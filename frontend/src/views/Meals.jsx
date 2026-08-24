import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

const PRETTY = (s) => s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());

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
            <span className="mname">{PRETTY(s.service)}</span>
            <span className="mhc">{s.headcount}</span>
          </label>
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

const money = (c) => `$${(c / 100).toFixed(2)}`;
