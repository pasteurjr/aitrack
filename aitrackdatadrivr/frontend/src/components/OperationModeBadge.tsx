import React from 'react';
import { resolveOperationMode } from '../config/operationMode';

interface OperationModeBadgeProps {
  modeValue?: string;
}

const OperationModeBadge: React.FC<OperationModeBadgeProps> = ({
  modeValue = process.env.REACT_APP_OPERATION_MODE,
}) => {
  const presentation = resolveOperationMode(modeValue);

  return (
    <span
      role="status"
      aria-label={`Ambiente: ${presentation.label}`}
      title={presentation.description}
      style={{
        alignItems: 'center',
        backgroundColor: presentation.backgroundColor,
        border: `1px solid ${presentation.color}`,
        borderRadius: '999px',
        color: presentation.color,
        display: 'inline-flex',
        fontSize: '10px',
        fontWeight: 800,
        letterSpacing: '0.06em',
        padding: '4px 8px',
        whiteSpace: 'nowrap',
      }}
    >
      AMBIENTE: {presentation.label}
    </span>
  );
};

export default OperationModeBadge;
