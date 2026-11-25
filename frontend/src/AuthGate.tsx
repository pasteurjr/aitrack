import React, { FormEvent, ReactNode, useEffect, useState } from 'react';

import { authApi } from './apiClient';


export default function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    authApi.me().then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)).finally(() => setReady(true));
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await authApi.login(email, password);
      setAuthenticated(true);
      setPassword('');
    } catch {
      setError('E-mail ou senha inválidos.');
    }
  };

  if (!ready) return <div className="vh-100 d-flex align-items-center justify-content-center">Verificando sessão…</div>;
  if (!authenticated) return (
    <main className="vh-100 bg-dark text-light d-flex align-items-center justify-content-center">
      <form onSubmit={submit} className="p-4 rounded bg-secondary" style={{ width: 360, maxWidth: 'calc(100vw - 32px)' }}>
        <h1 className="h4">AITrack</h1>
        <label className="form-label" htmlFor="email">E-mail</label>
        <input id="email" type="email" autoComplete="username" required className="form-control mb-2" value={email} onChange={event => setEmail(event.target.value)} />
        <label className="form-label" htmlFor="password">Senha</label>
        <input id="password" type="password" autoComplete="current-password" required className="form-control mb-3" value={password} onChange={event => setPassword(event.target.value)} />
        {error && <div role="alert" className="alert alert-danger">{error}</div>}
        <button className="btn btn-success w-100" type="submit">Entrar</button>
      </form>
    </main>
  );
  return <div style={{ height: '100%' }}><button className="btn btn-sm btn-light position-fixed bottom-0 end-0 m-2" style={{ zIndex: 2000 }} onClick={() => authApi.logout().finally(() => setAuthenticated(false))}>Sair</button>{children}</div>;
}
