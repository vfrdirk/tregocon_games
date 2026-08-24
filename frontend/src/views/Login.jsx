import React, { useState } from 'react';
import { api } from '../api.js';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [err, setErr] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    try { await api('/api/auth/login', { method: 'POST', body: { email, password: pw } }); await onLogin(); }
    catch (e) { setErr(e.message); }
  };
  return (
    <form className="card" onSubmit={submit}>
      <h2>Log in</h2>
      <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      <button type="submit">Log in</button>
      {err && <p className="err">{err}</p>}
    </form>
  );
}
