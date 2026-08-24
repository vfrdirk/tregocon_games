import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Announcements() {
  const [list, setList] = useState([]);
  const [body, setBody] = useState('');
  const [err, setErr] = useState('');

  const load = async () => { try { setList((await api('/api/announcements')).announcements); } catch (e) { setErr(e.message); } };
  useEffect(() => { load(); }, []);

  const post = async (e) => {
    e.preventDefault();
    try { await api('/api/announcements', { method: 'POST', body: { body } }); setBody(''); await load(); }
    catch (e) { setErr(e.message); }
  };

  return (
    <div>
      <h2>Announcements</h2>
      <div className="card">
        {list.map((a) => <div key={a.id} className="ann">{a.body}</div>)}
        {list.length === 0 && <p className="muted">Nothing posted yet.</p>}
      </div>
      <form className="card" onSubmit={post}>
        <textarea placeholder="Post an announcement" value={body} onChange={(e) => setBody(e.target.value)} />
        <button type="submit">Post</button>
      </form>
      {err && <p className="err">{err}</p>}
    </div>
  );
}
