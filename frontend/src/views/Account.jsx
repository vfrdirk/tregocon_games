import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Account({ onLogin }) {
  const [me, setMe] = useState(null);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [optIn, setOptIn] = useState(false);
  const [pw, setPw] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [confirm, setConfirm] = useState('');

  const load = async () => {
    const m = await api('/api/auth/me');
    setMe(m); setName(m.display_name || ''); setPhone(m.phone || '');
    setOptIn(m.sms_opt_in !== false);
  };
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const save = async (e) => {
    e.preventDefault(); setMsg(''); setErr('');
    try {
      const body = { display_name: name, phone, sms_opt_in: optIn };
      if (pw) body.password = pw;
      const r = await api('/api/auth/me', { method: 'PUT', body });
      setMe(r); setMsg('Saved'); setPw('');
    } catch (e) { setErr(e.message); }
  };

  const del = async () => {
    if (confirm.trim().toUpperCase() !== 'DELETE') { setErr('Type DELETE to confirm'); return; }
    try {
      await api('/api/auth/me', { method: 'DELETE' });
      await api('/api/auth/logout', { method: 'POST' });
      onLogin && onLogin();
      window.location.reload();
    } catch (e) { setErr(e.message); }
  };

  if (!me) return <div className="card" style={{ marginTop: '1rem' }}><p className="muted">Loading…</p></div>;

  return (
    <div className="card" style={{ marginTop: '1rem' }}>
      <h3>Account</h3>
      <form onSubmit={save}>
        <label>Display name
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>Mobile number (for SMS)
          <input placeholder="+16125551234" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
        <label className="row">
          <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} />
          <span>Receive SMS notifications (event updates only)</span>
        </label>
        <label>New password (leave blank to keep)
          <input type="password" placeholder="min 8 chars" value={pw} onChange={(e) => setPw(e.target.value)} />
        </label>
        <button type="submit">Save changes</button>
        {msg && <p className="ok">{msg}</p>}
      </form>
      <hr style={{ borderColor: 'var(--border)', margin: '1rem 0' }} />
      <h3 style={{ color: 'var(--err)' }}>Delete account</h3>
      <p className="muted">Permanently removes your profile, event selections, and uploaded photos.</p>
      <input placeholder='type DELETE to confirm' value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      <button type="button" className="del" style={{ color: 'var(--err)', border: '1px solid var(--err)', background: 'transparent', marginTop: '.5rem' }} onClick={del}>Delete my account</button>
      {err && <p className="err">{err}</p>}
    </div>
  );
}
