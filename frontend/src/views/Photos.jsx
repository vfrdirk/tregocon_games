import React, { useEffect, useState } from 'react';
import { api, SSE_BASE } from '../api.js';

export default function Photos() {
  const [photos, setPhotos] = useState([]);
  const [people, setPeople] = useState([]);
  const [games, setGames] = useState([]);
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState('');
  const [attendees, setAttendees] = useState([]);
  const [gameSel, setGameSel] = useState([]);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = async () => {
    const [p, pe, g] = await Promise.all([api('/api/photos'), api('/api/people'), api('/api/games')]);
    setPhotos(p.photos); setPeople(pe.people); setGames(g.games);
  };
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const toggle = (list, setList, id) => setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  const upload = async (e) => {
    e.preventDefault(); setErr(''); setMsg('');
    if (!file) return setErr('Choose an image first');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('caption', caption);
      fd.append('attendees', JSON.stringify(attendees));
      fd.append('games', JSON.stringify(gameSel));
      await api('/api/photos', { method: 'POST', body: fd, raw: true });
      setFile(null); setCaption(''); setAttendees([]); setGameSel([]);
      setMsg('Uploaded!'); await load();
    } catch (e) { setErr(e.message); }
  };

  return (
    <div>
      <h2>Event Photos</h2>
      <p className="muted">Share pictures from the weekend. Tag who's in them and which game.</p>
      <form className="card" onSubmit={upload}>
        <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} />
        <input placeholder="Caption" value={caption} onChange={(e) => setCaption(e.target.value)} />
        <details>
          <summary>Tag attendees ({attendees.length})</summary>
          <div className="chips">
            {people.map((u) => (
              <button type="button" key={u.id} className={attendees.includes(u.id) ? 'chip on' : 'chip'} onClick={() => toggle(attendees, setAttendees, u.id)}>{u.name}</button>
            ))}
            {people.length === 0 && <span className="muted">No attendees yet.</span>}
          </div>
        </details>
        <details>
          <summary>Tag games ({gameSel.length})</summary>
          <div className="chips">
            {games.filter((g) => g.status !== 'cancelled').map((g) => (
              <button type="button" key={g.id} className={gameSel.includes(g.id) ? 'chip on' : 'chip'} onClick={() => toggle(gameSel, setGameSel, g.id)}>{g.title}</button>
            ))}
            {games.length === 0 && <span className="muted">No games yet.</span>}
          </div>
        </details>
        <button type="submit">Upload</button>
      </form>
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}

      <div className="gallery">
        {photos.map((p) => (
          <div key={p.id} className="photo">
            <img src={p.url} alt={p.caption || 'event photo'} loading="lazy" />
            {p.caption && <div className="cap">{p.caption}</div>}
            {(p.attendees?.length > 0 || p.games?.length > 0) && (
              <div className="tags">
                {p.attendees?.map((a) => <span key={a} className="tag att">@{a}</span>)}
                {p.games?.map((g) => <span key={g} className="tag game">{g}</span>)}
              </div>
            )}
          </div>
        ))}
        {photos.length === 0 && <p className="muted">No photos yet — be the first to share!</p>}
      </div>
    </div>
  );
}
