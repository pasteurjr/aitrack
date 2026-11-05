import React from 'react';

export type AsyncDataStateVariant = 'loading' | 'empty' | 'error' | 'stale';

interface AsyncDataStateProps {
  variant: AsyncDataStateVariant;
  message: string;
  title?: string;
  onRetry?: () => void;
  onBack?: () => void;
  compact?: boolean;
}

const PRESENTATION: Record<AsyncDataStateVariant, { icon: string; defaultTitle: string; color: string }> = {
  loading: { icon: '⏳', defaultTitle: 'Carregando', color: '#93c5fd' },
  empty: { icon: '○', defaultTitle: 'Nenhum dado encontrado', color: '#9ca3af' },
  error: { icon: '⚠', defaultTitle: 'Informação indisponível', color: '#fca5a5' },
  stale: { icon: '◷', defaultTitle: 'Dados desatualizados', color: '#fbbf24' },
};

const AsyncDataState: React.FC<AsyncDataStateProps> = ({
  variant,
  message,
  title,
  onRetry,
  onBack,
  compact = false,
}) => {
  const presentation = PRESENTATION[variant];
  const role = variant === 'error' ? 'alert' : 'status';

  return (
    <div
      role={role}
      data-state={variant}
      style={{
        alignItems: 'center',
        backgroundColor: compact ? '#292524' : '#1f2937',
        border: compact ? `1px solid ${presentation.color}` : 'none',
        borderRadius: compact ? '6px' : 0,
        display: 'flex',
        flex: compact ? undefined : 1,
        flexDirection: compact ? 'row' : 'column',
        gap: compact ? '8px' : '12px',
        justifyContent: 'center',
        marginBottom: compact ? '12px' : 0,
        padding: compact ? '8px 10px' : '24px',
      }}
    >
      <span aria-hidden="true" style={{ color: presentation.color, fontSize: compact ? '16px' : '28px' }}>
        {presentation.icon}
      </span>
      <div style={{ flex: compact ? 1 : undefined, textAlign: compact ? 'left' : 'center' }}>
        <strong style={{ color: presentation.color, display: 'block', fontSize: compact ? '12px' : '15px' }}>
          {title ?? presentation.defaultTitle}
        </strong>
        <span style={{ color: '#d1d5db', display: 'block', fontSize: '12px', lineHeight: 1.5 }}>
          {message}
        </span>
      </div>
      {(onBack || onRetry) && (
        <div style={{ display: 'flex', gap: '8px' }}>
          {onBack && (
            <button type="button" onClick={onBack} style={styles.secondaryButton}>
              Voltar
            </button>
          )}
          {onRetry && (
            <button type="button" onClick={onRetry} style={styles.retryButton}>
              Tentar novamente
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  retryButton: {
    backgroundColor: '#b91c1c',
    border: 'none',
    borderRadius: '6px',
    color: '#fff',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 700,
    padding: '8px 12px',
  },
  secondaryButton: {
    backgroundColor: '#374151',
    border: 'none',
    borderRadius: '6px',
    color: '#f9fafb',
    cursor: 'pointer',
    fontSize: '12px',
    padding: '8px 12px',
  },
};

export default AsyncDataState;
