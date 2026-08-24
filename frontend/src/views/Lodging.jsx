import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

const NIGHTS = ['thu', 'fri', 'sat'];
const LABEL = { thu: 'Thu', fri: 'Fri', sat: 'Sat' };
const money = (c) => `$${(c / 100).toFixed(2)}`;
const BED = (b) => (b === 'double' ? '2 beds' : 'queen');

export default function Lodging() {
  const [data, setData] = useState(null);
  const [mine, setMine] = useState(null);
  const [sel, setSel] = useState({ room: null, nights: [] });
  const [companion, setCompanion] = useState('');
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
    const companions = companion.trim() ? [companion.trim()] : [];
    try {
      const r = await api('/api/lodging/reserve', { method: 'POST', body: { room_id: sel.room, nights: sel.nights, commitment_status: 'committed', companions } });
      setMsg(`Reserved! ${r.nights.join(', ')} — ${money(r.cost_cents)}${r.companions.length ? ` (incl. ${r.companions.join(', ')})` : ''}`);
      setSel({ room: null, nights: [] }); setCompanion('');
      await load();
    } catch (e) { setErr(e.message); }
  };

  const cancel = async () => {
    try { await api('/api/lodging/reserve', { method: 'DELETE' }); setMsg('Reservation released'); await load(); }
    catch (e) { setErr(e.message); }
  };

  if (!data) return <div>Loading…</div>;

  // group rooms by floor for display
  const byFloor = {};
  for (const lg of data.lodges) for (const r of lg.rooms) {
    (byFloor[r.floor] ||= {})[r.label] = r;
  }
  const FLOOR_ORDER = ['upstairs', 'main', 'down'];
  const FLOOR_LABEL = { upstairs: 'Upstairs', main: 'Main Floor', down: 'Downstairs' };
  const selectedRoom = sel.room ? Object.values(byFloor).flatMap(Object.values).find((r) => r.id === sel.room) : null;
  const maxCompanions = selectedRoom ? selectedRoom.capacity - selectedRoom.spaces_left - 1 : 0;

  return (
    <div>
      <h2>Lodging — {data.event?.name}</h2>
      <p className="muted">{money(rate)} / person / night · no discounts · companions billed same as a person</p>
      {mine && (
        <div className="card">
          <h3>Your room</h3>
          <p>{mine.room_label} · {mine.nights.map((n) => LABEL[n]).join(', ')} · {money(mine.cost_cents)} · {mine.payment}</p>
          {mine.companions?.length > 0 && <p className="muted">Companions: {mine.companions.join(', ')}</p>}
          <button onClick={cancel}>Release</button>
        </div>
      )}
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}

      {FLOOR_ORDER.map((floor) => {
        const rooms = Object.values(byFloor[floor] || {});
        if (!rooms.length) return null;
        return (
          <div className="card" key={floor}>
            <h3>{FLOOR_LABEL[floor]}</h3>
            <div className="rooms">
              {rooms.map((r) => (
                <div key={r.id} className={'room' + (sel.room === r.id ? ' sel' : '') + (r.spaces_left === 0 ? ' full' : '')} onClick={() => r.spaces_left > 0 && setSel((s) => ({ ...s, room: r.id }))}>
                  <div className="rlabel">{r.label} <small>({BED(r.bed_config)})</small></div>
                  <div className="rcap">{r.spaces_left > 0 ? `${r.spaces_left} space(s) left` : 'FULL'}</div>
                  <div className="occupants">
                    {r.occupants.length === 0 && <div className="occ empty">— empty —</div>}
                    {r.occupants.map((o, i) => (
                      <div key={i} className={'occ' + (o.is_guest ? ' guest' : '')}>
                        <span className="oname">{o.display_name}{o.is_guest ? ' (guest)' : ''}</span>
                        <span className="onights">{o.nights.map((n) => LABEL[n]).join(', ')}</span>
                        <span className="ocost">{money(o.cost_cents)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {selectedRoom && (
        <div className="card">
          <h3>Reserve {selectedRoom.label} ({BED(selectedRoom.bed_config)})</h3>
          {NIGHTS.map((n) => (
            <label key={n} className="night">
              <input type="checkbox" checked={sel.nights.includes(n)} onChange={() => toggleNight(n)} /> {LABEL[n]}
            </label>
          ))}
          {maxCompanions > 0 && (
            <div style={{ marginTop: '.5rem' }}>
              <label>Add companion (spouse/child) — billed {money(rate)}/night
                <input placeholder="Full name" value={companion} onChange={(e) => setCompanion(e.target.value)} />
              </label>
            </div>
          )}
          <p className="muted">Total: {money(sel.nights.length * rate * (1 + (companion.trim() ? 1 : 0)))}</p>
          <button onClick={reserve}>Reserve</button>
        </div>
      )}
    </div>
  );
}
