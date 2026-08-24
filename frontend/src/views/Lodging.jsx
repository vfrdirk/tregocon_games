import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

const NIGHTS = ['thu', 'fri', 'sat'];
const LABEL = { thu: 'Thu', fri: 'Fri', sat: 'Sat' };
const money = (c) => `$${(c / 100).toFixed(2)}`;

export default function Lodging() {
  const [data, setData] = useState(null);
  const [mine, setMine] = useState(null);
  const [sel, setSel] = useState({ room: null, nights: [] });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = async () => {
    const [av, my] = await Promise.all([api('/api/lodging/availability'), api('/api/lodging/my-reservation')]);
    setData(av); setMine(my.reservation);
  };
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const rate = data?.event?.rate_per_night_cents ?? 5000;
  const toggleNight = (n) => setSel((s) => ({ ...s, nights: s.nights.includes(n) ? s.nights.filter((x) => x !== n) : [...s.nights, n] }));

  const reserve = async () => {
    setErr(''); setMsg('');
    if (!sel.room || sel.nights.length === 0) return setErr('Pick a room and at least one night');
    try {
      const r = await api('/api/lodging/reserve', { method: 'POST', body: { room_id: sel.room, nights: sel.nights, commitment_status: 'committed' } });
      setMsg(`Reserved! ${r.nights.join(', ')} — ${money(r.cost_cents)}`);
      setSel({ room: null, nights: [] });
      await load();
    } catch (e) { setErr(e.message); }
  };

  const cancel = async () => {
    try { await api('/api/lodging/reserve', { method: 'DELETE' }); setMsg('Reservation released'); await load(); }
    catch (e) { setErr(e.message); }
  };

  if (!data) return <div>Loading…</div>;

  return (
    <div>
      <h2>Lodging — {data.event?.name}</h2>
      <p className="muted">{money(rate)} / person / night</p>
      {mine && (
        <div className="card">
          <h3>Your room</h3>
          <p>{mine.room_label} · {mine.nights.map((n) => LABEL[n]).join(', ')} · {money(mine.cost_cents)} · {mine.payment}</p>
          <button onClick={cancel}>Release</button>
        </div>
      )}
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}
      {data.lodges.map((lg) => (
        <div className="card" key={lg.id}>
          <h3>{lg.name}</h3>
          <div className="rooms">
            {lg.rooms.map((r) => (
              <div key={r.id} className={'room' + (sel.room === r.id ? ' sel' : '') + (r.spaces_left === 0 ? ' full' : '')} onClick={() => r.spaces_left > 0 && setSel((s) => ({ ...s, room: r.id }))}>
                <div className="rlabel">{r.label} <small>({r.bed_config})</small></div>
                <div className="rcap">{r.spaces_left > 0 ? `${r.spaces_left} space(s) left` : 'FULL'}</div>
                <div className="occupants">
                  {r.occupants.length === 0 && <div className="occ empty">— empty —</div>}
                  {r.occupants.map((o) => (
                    <div key={o.user_id} className="occ">
                      <span className="oname">{o.display_name}</span>
                      <span className="onights">{o.nights.map((n) => LABEL[n]).join(', ')}</span>
                      <span className="ocost">{money(o.cost_cents)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      {sel.room && (
        <div className="card">
          <h3>Pick nights</h3>
          {NIGHTS.map((n) => (
            <label key={n} className="night">
              <input type="checkbox" checked={sel.nights.includes(n)} onChange={() => toggleNight(n)} /> {LABEL[n]}
            </label>
          ))}
          <p className="muted">Total: {money(sel.nights.length * rate)}</p>
          <button onClick={reserve}>Reserve selected</button>
        </div>
      )}
    </div>
  );
}
