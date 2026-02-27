-- Migration 004: Seed Mock Alerts for Demo
-- Creates initial alerts to demonstrate the system

-- Insert 3-4 sample alerts for demonstration
INSERT INTO monitor_alertas (monitor_id, veiculomonitor_id, device_id, titulo, mensagem, severidade, tipo, status, criado_em, total_eventos_relacionados)
SELECT
    1,
    vm.id,
    vm.device_id,
    CONCAT('Score baixo detectado: ', vm.device_id),
    CONCAT('Veículo ', vm.device_id, ' apresentou comportamento de risco com múltiplos eventos de frenagem brusca e excesso de velocidade.'),
    'high',
    'safety',
    'pending',
    NOW() - INTERVAL 2 HOUR,
    15
FROM veiculomonitor vm
WHERE vm.monitor_id = 1 AND vm.device_id = 'SIM-1001'
LIMIT 1;

INSERT INTO monitor_alertas (monitor_id, veiculomonitor_id, device_id, titulo, mensagem, severidade, tipo, status, criado_em, total_eventos_relacionados)
SELECT
    2,
    vm.id,
    vm.device_id,
    CONCAT('Padrão crítico detectado: ', vm.device_id),
    CONCAT('Veículo ', vm.device_id, ' com score de 48.3 e 24 eventos críticos nas últimas 2 horas.'),
    'critical',
    'safety',
    'pending',
    NOW() - INTERVAL 1 HOUR,
    24
FROM veiculomonitor vm
WHERE vm.monitor_id = 2 AND vm.device_id = 'SIM-1003'
LIMIT 1;

INSERT INTO monitor_alertas (monitor_id, veiculomonitor_id, device_id, titulo, mensagem, severidade, tipo, status, criado_em, total_eventos_relacionados)
SELECT
    4,
    vm.id,
    vm.device_id,
    CONCAT('Eficiência baixa: ', vm.device_id),
    CONCAT('Veículo ', vm.device_id, ' apresentou alto consumo com múltiplas acelerações bruscas.'),
    'medium',
    'efficiency',
    'acknowledged',
    NOW() - INTERVAL 4 HOUR,
    12
FROM veiculomonitor vm
WHERE vm.monitor_id = 4 AND vm.device_id = 'SIM-1007'
LIMIT 1;

INSERT INTO monitor_alertas (monitor_id, veiculomonitor_id, device_id, titulo, mensagem, severidade, tipo, status, criado_em, total_eventos_relacionados)
SELECT
    3,
    vm.id,
    vm.device_id,
    CONCAT('Comportamento irregular: ', vm.device_id),
    CONCAT('Veículo ', vm.device_id, ' com score em queda constante - 18 eventos em 30 minutos.'),
    'high',
    'behavior',
    'pending',
    NOW() - INTERVAL 30 MINUTE,
    18
FROM veiculomonitor vm
WHERE vm.monitor_id = 3 AND vm.device_id = 'SIM-1004'
LIMIT 1;
