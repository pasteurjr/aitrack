import React from 'react';

interface DemoDataNoticeProps {
  detail: string;
}

const DemoDataNotice: React.FC<DemoDataNoticeProps> = ({ detail }) => (
  <div
    role="note"
    aria-label="Conteúdo de demonstração"
    style={{
      alignItems: 'center',
      backgroundColor: '#451a03',
      borderBottom: '1px solid #f59e0b',
      color: '#fef3c7',
      display: 'flex',
      flexShrink: 0,
      fontSize: '11px',
      gap: '8px',
      lineHeight: 1.35,
      padding: '7px 12px',
    }}
  >
    <strong style={{ color: '#fbbf24', whiteSpace: 'nowrap' }}>
      DEMONSTRAÇÃO — DADOS NÃO OPERACIONAIS
    </strong>
    <span aria-hidden="true">•</span>
    <span>{detail}</span>
  </div>
);

export default DemoDataNotice;
