import React, { useEffect, useState, useRef } from 'react';
import { api, SSE_BASE } from '../api.js';

export default function Photos({ user }) {
  const [photos, setPhotos] = useState([]);
  const [people, setPeople] = useState([]);
  const [games, setGames] = useState([]);
  const [files, setFiles] = useState([]);
  const [caption, setCaption] = useState('');
  const [attendees, setAttendees] = useState([]);
  const [gameSel, setGameSel] = useState([]);
  const [selected, setSelected] = useState([]); // photo ids for export
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [lightbox, setLightbox] = useState(null); // photo url

  const load = async () => {
    const [p, pe, g] = await Promise.all([api('/api/photos'), api('/api/people'), api('/api/games')]);
    setPhotos(p.photos); setPeople(pe.people); setGames(g.games);
  };
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const toggle = (list, setList, id) => setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  const isAdmin = user.role === 'admin';

  const upload = async (e) => {
    e.preventDefault(); setErr(''); setMsg('');
    if (files.length === 0) return setErr('Choose at least one image');
    try {
      const fd = new FormData();
      for (const f of files) fd.append('file', f);
      fd.append('caption', caption);
      fd.append('attendees', JSON.stringify(attendees));
      fd.append('games', JSON.stringify(gameSel));
      await api('/api/photos', { method: 'POST', body: fd });
      setFiles([]); setCaption(''); setAttendees([]); setGameSel([]);
      setMsg(`Uploaded ${files.length} photo(s)!`); await load();
    } catch (e) { setErr(e.message); }
  };

  const del = async (id) => {
    if (!isAdmin) return;
    if (!confirm('Delete this photo?')) return;
    try { await api(`/api/photos/${id}`, { method: 'DELETE' }); await load(); }
    catch (e) { setErr(e.message); }
  };
  const exportZip = () => {
    if (selected.length === 0) return setErr('Select photos to export first');
    window.open(`/api/photos/export?ids=${selected.join(',')}`, '_blank');
  };
  const toggleSelect = (id) => setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);

  return (
    <div>
      <h2>Event Photos</h2>
      <p className="muted">Share pictures from the weekend. Tag who's in them and which game.</p>
      <form className="card" onSubmit={upload}>
        <input type="file" accept="image/*" multiple onChange={(e) => setFiles([...e.target.files])} />
        {files.length > 0 && <p className="muted">{files.length} file(s) selected</p>}
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

      <div className="row between">
        <h3>Gallery ({photos.length})</h3>
        <div>
          <button onClick={() => setSelected(selected.length === photos.length ? [] : photos.map((p) => p.id))}>
            {selected.length === photos.length ? 'Deselect all' : 'Select all'}
          </button>
          <button className="accent" onClick={exportZip} disabled={selected.length === 0}>Export selected ({selected.length})</button>
        </div>
      </div>

      <div className="gallery">
        {photos.map((p) => (
          <div key={p.id} className={'photo' + (selected.includes(p.id) ? ' sel' : '')}>
            <div className="phototop">
              <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggleSelect(p.id)} />
              {isAdmin && <button className="del" onClick={() => del(p.id)} title="Delete">✕</button>}
            </div>
            <img src={p.url} alt={p.caption || 'event photo'} loading="lazy" onClick={() => setLightbox(p.url)} />
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

      {lightbox && <Lightbox url={lightbox} onClose={() => setLightbox(null)} />}
    </div>
  );
}

function Lightbox({ url, onClose }) {
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef(null);
  return (
    <div className="lightbox" onClick={onClose}>
      <div className="lbtoolbar" onClick={(e) => e.stopPropagation()}>
        <button onClick={() => setScale((s) => Math.min(4, s + 0.25))}>Zoom +</button>
        <button onClick={() => setScale((s) => Math.max(1, s - 0.25))}>Zoom −</button>
        <button onClick={() => { setScale(1); setPos({ x: 0, y: 0 }); }}>Reset</button>
        <button onClick={onClose}>Close</button>
      </div>
      <img
        src={url} alt=""
        style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`, cursor: scale > 1 ? 'grab' : 'zoom-in' }}
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => { e.preventDefault(); setScale((s) => Math.min(4, Math.max(1, s + (e.deltaY < 0 ? 0.25 : -0.25)))); }}
        onMouseDown={(e) => { if (scale > 1) { drag.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }; } }}
        onMouseMove={(e) => { if (drag.current && scale > 1) setPos({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y }); }}
        onMouseUp={() => { drag.current = null; }}
      />
    </div>
  );
}
