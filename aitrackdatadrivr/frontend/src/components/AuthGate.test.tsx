import { vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';

import { authService } from '../services/apiService';
import AuthGate from './AuthGate';

vi.mock('../services/apiService', () => ({ authService: {
  me: vi.fn(), login: vi.fn(), logout: vi.fn(), recover: vi.fn(),
} }));

const service = authService as jest.Mocked<typeof authService>;

test('exige login e não diferencia recuperação de conta', async () => {
  service.me.mockRejectedValueOnce(new Error('401'));
  service.login.mockRejectedValueOnce(new Error('401'));
  service.recover.mockResolvedValueOnce({ data: { status: 'accepted' } } as any);
  const { container } = render(<AuthGate><div>Aplicação protegida</div></AuthGate>);
  expect(await screen.findByRole('heading', { name: 'AITrack + DataDrivr' })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'x@example.test' } });
  fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'errada' } });
  fireEvent.click(screen.getByRole('button', { name: 'Entrar' }));
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('E-mail ou senha inválidos');
  expect(screen.getByLabelText('E-mail')).toHaveAttribute('aria-invalid', 'true');
  expect(screen.getByLabelText('E-mail')).toHaveAttribute('aria-describedby', alert.id);
  expect(screen.getByLabelText('Senha')).toHaveAttribute('aria-describedby', alert.id);
  expect(await axe(container)).toHaveNoViolations();
  fireEvent.click(screen.getByRole('button', { name: 'Esqueci minha senha' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Se a conta existir');
});

test('tela de login não tem violações axe no estado inicial', async () => {
  service.me.mockRejectedValueOnce(new Error('401'));
  const { container } = render(<AuthGate><div>Aplicação protegida</div></AuthGate>);
  await screen.findByRole('heading', { name: 'AITrack + DataDrivr' });
  expect(await axe(container)).toHaveNoViolations();
});

test('restaura sessão e permite logout', async () => {
  service.me.mockResolvedValueOnce({ data: { user: { display_name: 'Operador' } } } as any);
  service.logout.mockResolvedValueOnce({ data: {} } as any);
  render(<AuthGate><div>Aplicação protegida</div></AuthGate>);
  expect(await screen.findByText('Aplicação protegida')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Sair da conta de Operador' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'AITrack + DataDrivr' })).toBeInTheDocument());
});
