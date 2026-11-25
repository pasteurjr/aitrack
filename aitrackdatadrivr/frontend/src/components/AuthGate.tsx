import React, { createContext, FormEvent, ReactNode, useContext, useEffect, useState } from 'react';

import { authService } from '../services/apiService';
import type { AuthSession } from '../types/auth';

const AuthContext = createContext<AuthSession | null>(null);
export const useAuth = () => useContext(AuthContext);

export default function AuthGate({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [recoverySent, setRecoverySent] = useState(false);

  useEffect(() => {
    authService.me().then(response => setSession(response.data)).catch(() => setSession(null)).finally(() => setChecking(false));
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const response = await authService.login(email, password);
      setSession(response.data);
      setPassword('');
    } catch {
      setError('E-mail ou senha inválidos.');
    }
  };

  const recover = async () => {
    if (!email) return;
    await authService.recover(email).catch(() => undefined);
    setRecoverySent(true);
  };

  if (checking) return <div role="status" style={styles.center}>Verificando sessão…</div>;
  if (!session) return (
    <main style={styles.center}>
      <form onSubmit={submit} style={styles.card}>
        <h1 style={{ marginTop: 0 }}>AITrack + DataDrivr</h1>
        <p>Acesso ao monitoramento veicular</p>
        <label htmlFor="auth-email">E-mail</label>
        <input id="auth-email" type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} style={styles.input} />
        <label htmlFor="auth-password">Senha</label>
        <input id="auth-password" type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} style={styles.input} />
        {error && <div role="alert" style={styles.error}>{error}</div>}
        <button type="submit" style={styles.primary}>Entrar</button>
        <button type="button" onClick={recover} style={styles.link}>Esqueci minha senha</button>
        {recoverySent && <p role="status">Se a conta existir, as instruções serão enviadas.</p>}
      </form>
    </main>
  );
  return (
    <div style={{ height: '100%' }}>
      <button
        type="button"
        aria-label={`Sair da conta de ${session.user.display_name}`}
        onClick={() => authService.logout().finally(() => setSession(null))}
        style={styles.logout}
      >Sair</button>
      <AuthContext.Provider value={session}>{children}</AuthContext.Provider>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  center: { minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#111827', color: '#f3f4f6' },
  card: { width: 360, maxWidth: 'calc(100vw - 32px)', padding: 28, borderRadius: 10, background: '#1f2937', display: 'grid', gap: 10 },
  input: { padding: 10, borderRadius: 6, border: '1px solid #4b5563', background: '#111827', color: 'white' },
  primary: { padding: 10, border: 0, borderRadius: 6, background: '#059669', color: 'white', fontWeight: 700 },
  link: { border: 0, background: 'transparent', color: '#93c5fd' },
  error: { color: '#fecaca' },
  logout: { position: 'fixed', right: 12, bottom: 12, zIndex: 2000, padding: '7px 12px' },
};
