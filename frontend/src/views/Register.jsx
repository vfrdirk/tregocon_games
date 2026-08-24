import React, { useState } from 'react';
import { api } from '../api.js';

export default function Register() {
  const [form, setForm] = useState({ email: '', display_name: '', password: '', phone: '' });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    setErr(''); setMsg('');
    try {
      const r = await api('/api/auth/register', { method: 'POST', body: form });
      setMsg(r.message);
    } catch (e) { setErr(e.message); }
  };
  return (
    <form className="card" onSubmit={submit}>
      <h2>Request account</h2>
      <input placeholder="display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
      <input placeholder="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <input placeholder="phone (optional, for SMS)" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
      <input type="password" placeholder="password (8+ chars)" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
      <button type="submit">Register</button>
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}
    </form>
  );
}
