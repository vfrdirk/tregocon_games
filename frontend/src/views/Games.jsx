import React, { useEffect, useRef, useState } from 'react';
import { api, SSE_BASE } from '../api.js';

const TB = { now: 'Now', after_breakfast: 'After breakfast', noon: 'Noon', evening: 'Evening', specific_time: 'Specific time' };
const fmtTime = (iso) => { if (!iso) return ''; return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); };

export default function Games({ user }) {
  const [games, setGames] = useState([]);
  const [title, setTitle] = useState('');
  const [when, setWhen] = useState('');
  const [maxPlayers, setMaxPlayers] = useState('');
  const [showCancelled, setShowCancelled] = useState(false);
  const [err, setErr] = useState('');
  const esRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(SSE_BASE + '/api/games/stream', { withCredentials: true });
    es.onmessage = (e) => { try { setGames(JSON.parse(e.data).games); } catch {} };
    es.onerror = () => {};
    esRef.current = es;
    return () => es.close();
  }, []);

  const post = async (e) => {
    e.preventDefault(); setErr('');
    if (!title.trim()) return setErr('Title required');
    const body = { title, when: when.trim() || null };
    if (maxPlayers.trim()) body.max_players = parseInt(maxPlayers, 10);
    try { await api('/api/games', { method: 'POST', body }); setTitle(''); setWhen(''); setMaxPlayers(''); }
    catch (e) { setErr(e.message); }
  };
  const signup = async (id, interest) => {
    try { await api(`/api/games/${id}/signup`, { method: 'POST', body: { interest } }); }
    catch (e) { setErr(e.message); }
  };
  const leave = async (id) => { try { await api(`/api/games/${id}/signup`, { method: 'DELETE' }); } catch (e) { setErr(e.message); } };
  const setStatus = async (id, status) => { try { await api(`/api/games/${id}/status`, { method: 'POST', body: { status } }); } catch (e) { setErr(e.message); } };

  const playing = games.filter((g) => g.status === 'playing');
  const open = games.filter((g) => g.status === 'open' || g.status === 'full');
  const played = games.filter((g) => g.status === 'played');
  const cancelled = games.filter((g) => g.status === 'cancelled');

  const whenLabel = (g) => {
    if (g.when) return g.when;
    if (g.time_box) return TB[g.time_box] || g.time_box;
    return '';
  };
  const countLabel = (g) => (g.max_players ? `${g.in_count} / ${g.max_players}` : `${g.in_count}`);

  const Card = ({ g }) => {
    const isPlayed = g.status === 'played';
    const isPlaying = g.status === 'playing';
    const full = g.full;
    const [expanded, setExpanded] = useState(false);
    if (isPlayed) {
      const count = g.in_count + g.maybe_count;
      return (
        <div className="gcard status-played" title={g.title}>
          <span className="gplayed" onClick={() => setExpanded((v) => !v)} style={{ cursor: 'pointer' }}>
            {g.title} {count > 0 && <span className="played-count">· {count} player{count === 1 ? '' : 's'}</span>}
            <span className="expand-cue">{expanded ? ' ▾' : ' ▸'}</span>
          </span>
          {expanded && (
            <div className="played-detail">
              {g.in_names?.length > 0 && <div className="names in">▶ Played: {g.in_names.join(', ')}</div>}
              {g.maybe_names?.length > 0 && <div className="names maybe">? Maybe: {g.maybe_names.join(', ')}</div>}
              {count === 0 && <div className="muted">No players recorded</div>}
            </div>
          )}
        </div>
      );
    }
    return (
      <div key={g.id} className={'gcard status-' + g.status + (isPlaying ? ' nowplaying' : '') + (full ? ' full' : '')}>
        <div className="ghead">
          <strong>{g.title}</strong>
          {isPlaying && <span className="live">● NOW PLAYING</span>}
          {whenLabel(g) && <span className="tb">{whenLabel(g)}</span>}
          {g.posted_at && <span className="posted">· {fmtTime(g.posted_at)}</span>}
          {g.location && <span className="loc">@ {g.location}</span>}
        </div>
        {g.description && <div className="gdesc">{g.description}</div>}
        <div className="gsign">
          <span className="in">In: {countLabel(g)}{full && ' (full)'}</span>
          <span className="maybe">Maybe: {g.maybe_count}</span>
        </div>
        {g.in_names?.length > 0 && <div className="names in">▶ {g.in_names.join(', ')}</div>}
        {g.maybe_names?.length > 0 && <div className="names maybe">? {g.maybe_names.join(', ')}</div>}
        <div className="gacts">
          {g.my_interest === 'in' ? (
            <>
              <button onClick={() => signup(g.id, 'maybe')}>Maybe</button>
              <button onClick={() => leave(g.id)}>Leave</button>
            </>
          ) : g.my_interest === 'maybe' ? (
            <>
              <button onClick={() => signup(g.id, 'in')}>I'm in!</button>
              <button onClick={() => leave(g.id)}>Leave</button>
            </>
          ) : (
            <>
              <button onClick={() => signup(g.id, 'in')} disabled={full}>I'm in!</button>
              <button onClick={() => signup(g.id, 'maybe')}>Maybe</button>
            </>
          )}
          {(user.role === 'admin' || g.proposed_by === user.id) && (
            <>
              {!isPlaying && <button className="start" onClick={() => setStatus(g.id, 'playing')}>Start</button>}
              <button onClick={() => setStatus(g.id, 'played')}>Played</button>
              <button onClick={() => setStatus(g.id, 'cancelled')}>Cancel</button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <div>
      <h2>On-Deck Games</h2>
      <p className="muted">Post a game; others click in. You're auto-joined when you post. Live board updates automatically.</p>
      <form className="card" onSubmit={post}>
        <input placeholder="Game title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input placeholder='When? e.g. "ASAP", "after dinner", "8pm" (optional)' value={when} onChange={(e) => setWhen(e.target.value)} />
        <input type="number" min="1" placeholder="Max players (optional)" value={maxPlayers} onChange={(e) => setMaxPlayers(e.target.value)} style={{ width: '11rem' }} />
        <button type="submit">Post game</button>
      </form>
      {err && <p className="err">{err}</p>}

      {playing.length > 0 && (
        <div className="section now"><h3>● Now Playing</h3><div className="games">{playing.map((g) => <Card key={g.id} g={g} />)}</div></div>
      )}
      <div className="section"><h3>On Deck</h3><div className="games">
        {open.map((g) => <Card key={g.id} g={g} />)}
        {open.length === 0 && <p className="muted">Nothing queued.</p>}
      </div></div>
      {played.length > 0 && (<div className="section done"><h3>Played</h3><div className="games played">{played.map((g) => <Card key={g.id} g={g} />)}</div></div>)}
      {cancelled.length > 0 && (
        <div className="section cancelled-section">
          <button className="collapse-toggle" onClick={() => setShowCancelled((v) => !v)}>
            {showCancelled ? '▾' : '▸'} Cancelled ({cancelled.length})
          </button>
          {showCancelled && <div className="games cancelled">{cancelled.map((g) => <Card key={g.id} g={g} />)}</div>}
        </div>
      )}
    </div>
  );
}
