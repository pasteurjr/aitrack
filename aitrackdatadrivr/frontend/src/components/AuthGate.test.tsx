import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { authService } from '../services/apiService';
import AuthGate from './AuthGate';

jest.mock('../services/apiService', () => ({ authService: {
  me: jest.fn(), login: jest.fn(), logout: jest.fn(), recover: jest.fn(),
} }));

const service = authService as jest.Mocked<typeof authService>;

test('exige login e não diferencia recuperação de conta', async () => {
  service.me.mockRejectedValueOnce(new Error('401'));
  service.login.mockRejectedValueOnce(new Error('401'));
  service.recover.mockResolvedValueOnce({ data: { status: 'accepted' } } as any);
  render(<AuthGate><div>Aplicação protegida</div></AuthGate>);
  expect(await screen.findByRole('heading', { name: 'AITrack + DataDrivr' })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'x@example.test' } });
  fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'errada' } });
  fireEvent.click(screen.getByRole('button', { name: 'Entrar' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha inválidos');
  fireEvent.click(screen.getByRole('button', { name: 'Esqueci minha senha' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Se a conta existir');
});

test('restaura sessão e permite logout', async () => {
  service.me.mockResolvedValueOnce({ data: { user: { display_name: 'Operador' } } } as any);
  service.logout.mockResolvedValueOnce({ data: {} } as any);
  render(<AuthGate><div>Aplicação protegida</div></AuthGate>);
  expect(await screen.findByText('Aplicação protegida')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Sair da conta de Operador' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'AITrack + DataDrivr' })).toBeInTheDocument());
});
