import React, { useEffect, useRef, useState } from 'react';
import { api, SSE_BASE } from '../api.js';

const TB = { now: 'Now', after_breakfast: 'After breakfast', noon: 'Noon', evening: 'Evening', specific_time: 'Specific time' };

export default function Games({ user }) {
  const [games, setGames] = useState([]);
  const [title, setTitle] = useState('');
  const [timeBox, setTimeBox] = useState('now');
  const [err, setErr] = useState('');
  const esRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(SSE_BASE + '/api/games/stream', { withCredentials: true });
    es.onmessage = (e) => { try { setGames(JSON.parse(e.data).games); } catch {} };
    es.onerror = () => {}; // keep-alive; browser auto-reconnects
    esRef.current = es;
    return () => es.close();
  }, []);

  const post = async (e) => {
    e.preventDefault(); setErr('');
    if (!title.trim()) return setErr('Title required');
    try { await api('/api/games', { method: 'POST', body: { title, time_box: timeBox } }); setTitle(''); }
    catch (e) { setErr(e.message); }
  };

  const signup = async (id, interest) => {
    try { await api(`/api/games/${id}/signup`, { method: 'POST', body: { interest } }); }
    catch (e) { setErr(e.message); }
  };
  const leave = async (id) => { try { await api(`/api/games/${id}/signup`, { method: 'DELETE' }); } catch (e) { setErr(e.message); } };
  const setStatus = async (id, status) => { try { await api(`/api/games/${id}/status`, { method: 'POST', body: { status } }); } catch (e) { setErr(e.message); } };

  return (
    <div>
      <h2>On-Deck Games</h2>
      <p className="muted">Post a game; others click in. Live board updates automatically.</p>
      <form className="card" onSubmit={post}>
        <input placeholder="Game title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <select value={timeBox} onChange={(e) => setTimeBox(e.target.value)}>
          {Object.entries(TB).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button type="submit">Post game</button>
      </form>
      {err && <p className="err">{err}</p>}
      <div className="games">
        {games.map((g) => (
          <div key={g.id} className={'gcard status-' + g.status}>
            <div className="ghead">
              <strong>{g.title}</strong> <span className="tb">{TB[g.time_box] || g.time_box}</span>
              {g.location && <span className="loc">@ {g.location}</span>}
            </div>
            <div className="gsign">
              <span className="in">In: {g.in_count}</span> <span className="maybe">Maybe: {g.maybe_count}</span>
              <span className="st">{g.status}</span>
            </div>
            <div className="gacts">
              {g.my_interest === 'in' ? (
                <>
                  <button onClick={() => signup(g.id, 'maybe')}>Switch to Maybe</button>
                  <button onClick={() => leave(g.id)}>Leave</button>
                </>
              ) : g.my_interest === 'maybe' ? (
                <>
                  <button onClick={() => signup(g.id, 'in')}>Switch to In</button>
                  <button onClick={() => leave(g.id)}>Leave</button>
                </>
              ) : (
                <>
                  <button onClick={() => signup(g.id, 'in')}>I'm in!</button>
                  <button onClick={() => signup(g.id, 'maybe')}>Maybe</button>
                </>
              )}
              {(user.role === 'admin' || g.proposed_by === user.id) && (
                <>
                  <button onClick={() => setStatus(g.id, 'played')}>Played</button>
                  <button onClick={() => setStatus(g.id, 'cancelled')}>Cancel</button>
                </>
              )}
            </div>
          </div>
        ))}
        {games.length === 0 && <p className="muted">No games posted yet.</p>}
      </div>
    </div>
  );
}
