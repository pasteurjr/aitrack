import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import AsyncDataState from './AsyncDataState';

describe('AsyncDataState', () => {
  it.each([
    ['loading', 'status', 'Carregando'],
    ['empty', 'status', 'Nenhum dado encontrado'],
    ['error', 'alert', 'Informação indisponível'],
    ['stale', 'status', 'Dados desatualizados'],
  ] as const)('apresenta o estado %s de forma acessível', (variant, role, title) => {
    render(<AsyncDataState variant={variant} message="Mensagem operacional" />);

    expect(screen.getByRole(role)).toHaveAttribute('data-state', variant);
    expect(screen.getByRole(role)).toHaveTextContent(title);
    expect(screen.getByRole(role)).toHaveTextContent('Mensagem operacional');
  });

  it('oferece nova tentativa quando a operação pode ser repetida', () => {
    const onRetry = jest.fn();
    render(<AsyncDataState variant="error" message="Falha" onRetry={onRetry} />);

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
