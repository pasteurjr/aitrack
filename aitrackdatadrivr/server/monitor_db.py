"""
Database layer for AI Monitor system
Provides CRUD operations for monitors, vehicles, analyses, and alerts
"""

import mysql.connector
from typing import List, Dict, Optional
from datetime import datetime
import json

DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'scadabr',
    'password': 'scadabr',
    'database': 'tracker'
}

def get_connection():
    """Get MySQL database connection"""
    return mysql.connector.connect(**DB_CONFIG)


# ==================== CRUD Monitores ====================

def get_all_monitors() -> List[Dict]:
    """Lista todos os monitores"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome, descricao, tipo_monitor, intervalo_analise, janela_contexto,
               eventos_minimos, score_threshold, gera_alertas, ativo, criado_em, atualizado_em,
               (SELECT COUNT(*) FROM monitoramento.monitor_targets
                 WHERE monitor_id = monitoramento.monitores.id AND ativo = TRUE) as veiculos_monitorados
        FROM monitoramento.monitores
        ORDER BY id
    """)

    monitors = cursor.fetchall()

    # Convert datetime to ISO format
    for monitor in monitors:
        if monitor['criado_em']:
            monitor['criado_em'] = monitor['criado_em'].isoformat()
        if monitor['atualizado_em']:
            monitor['atualizado_em'] = monitor['atualizado_em'].isoformat()

    cursor.close()
    conn.close()

    return monitors


def get_monitor_by_id(monitor_id: int) -> Optional[Dict]:
    """Retorna um monitor por ID"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome, descricao, tipo_monitor, intervalo_analise, janela_contexto,
               eventos_minimos, score_threshold, gera_alertas, ativo, criado_em, atualizado_em,
               (SELECT COUNT(*) FROM monitoramento.monitor_targets
                 WHERE monitor_id = monitoramento.monitores.id AND ativo = TRUE) as veiculos_monitorados
        FROM monitoramento.monitores
        WHERE id = %s
    """, (monitor_id,))

    monitor = cursor.fetchone()

    if monitor:
        if monitor['criado_em']:
            monitor['criado_em'] = monitor['criado_em'].isoformat()
        if monitor['atualizado_em']:
            monitor['atualizado_em'] = monitor['atualizado_em'].isoformat()

    cursor.close()
    conn.close()

    return monitor


def get_active_monitors() -> List[Dict]:
    """Retorna apenas monitores ativos"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome, descricao, tipo_monitor, intervalo_analise, janela_contexto,
               eventos_minimos, score_threshold, gera_alertas, ativo, criado_em, atualizado_em
        FROM monitoramento.monitores
        WHERE ativo = TRUE
        ORDER BY id
    """)

    monitors = cursor.fetchall()

    cursor.close()
    conn.close()

    return monitors


def create_monitor(data: Dict) -> int:
    """Cria novo monitor"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO monitoramento.monitores (nome, descricao, tipo_monitor, intervalo_analise, janela_contexto,
                             eventos_minimos, score_threshold, gera_alertas, ativo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data.get('nome'),
        data.get('descricao'),
        data.get('tipo_monitor', 'safety'),
        data.get('intervalo_analise', 300),
        data.get('janela_contexto', 1800),
        data.get('eventos_minimos', 3),
        data.get('score_threshold', 70.0),
        data.get('gera_alertas', True),
        data.get('ativo', True)
    ))

    monitor_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return monitor_id


def update_monitor(monitor_id: int, data: Dict) -> bool:
    """Atualiza monitor existente"""
    conn = get_connection()
    cursor = conn.cursor()

    fields = []
    values = []

    if 'nome' in data:
        fields.append('nome = %s')
        values.append(data['nome'])
    if 'descricao' in data:
        fields.append('descricao = %s')
        values.append(data['descricao'])
    if 'tipo_monitor' in data:
        fields.append('tipo_monitor = %s')
        values.append(data['tipo_monitor'])
    if 'intervalo_analise' in data:
        fields.append('intervalo_analise = %s')
        values.append(data['intervalo_analise'])
    if 'janela_contexto' in data:
        fields.append('janela_contexto = %s')
        values.append(data['janela_contexto'])
    if 'eventos_minimos' in data:
        fields.append('eventos_minimos = %s')
        values.append(data['eventos_minimos'])
    if 'score_threshold' in data:
        fields.append('score_threshold = %s')
        values.append(data['score_threshold'])
    if 'gera_alertas' in data:
        fields.append('gera_alertas = %s')
        values.append(data['gera_alertas'])
    if 'ativo' in data:
        fields.append('ativo = %s')
        values.append(data['ativo'])

    if not fields:
        cursor.close()
        conn.close()
        return False

    values.append(monitor_id)
    sql = f"UPDATE monitoramento.monitores SET {', '.join(fields)} WHERE id = %s"

    cursor.execute(sql, values)
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()

    return success


def toggle_monitor(monitor_id: int, ativo: bool) -> bool:
    """Ativa/desativa monitor"""
    return update_monitor(monitor_id, {'ativo': ativo})


# ==================== Veículos em Monitores ====================

def get_monitor_vehicles(monitor_id: int) -> List[Dict]:
    """Lista veículos de um monitor com JOIN para pegar device_id"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT mt.id, mt.monitor_id, mt.fonte_codigo AS tipo_veiculo,
               mt.legacy_veicod_tracker AS veicod_tracker,
               COALESCE(
                 mt.legacy_codusu_dirijabem,
                 (SELECT CAST(mi.valor_externo AS UNSIGNED)
                    FROM monitoramento.motorista_identidades mi
                   WHERE mi.driver_id = mt.driver_id
                     AND mi.fonte_codigo = 'dirijabem'
                     AND mi.tipo_identidade = 'user_id' AND mi.ativo = TRUE
                   LIMIT 1)
               ) AS codusu_dirijabem,
               COALESCE(
                 mt.legacy_device_id,
                 (SELECT vi.valor_externo
                    FROM monitoramento.veiculo_identidades vi
                   WHERE vi.vehicle_id = mt.vehicle_id
                     AND vi.fonte_codigo = 'tracker'
                     AND vi.tipo_identidade = 'device_id' AND vi.ativo = TRUE
                   ORDER BY vi.principal DESC, vi.id LIMIT 1),
                 CONCAT('APP-', (SELECT mi.valor_externo
                    FROM monitoramento.motorista_identidades mi
                   WHERE mi.driver_id = mt.driver_id
                     AND mi.fonte_codigo = 'dirijabem'
                     AND mi.tipo_identidade = 'user_id' AND mi.ativo = TRUE
                   LIMIT 1))
               ) AS device_id,
               mt.ativo, mt.atribuido_em, v.placa, d.nome AS nome_motorista
          FROM monitoramento.monitor_targets mt
     LEFT JOIN monitoramento.veiculos v ON v.id = mt.vehicle_id
     LEFT JOIN monitoramento.motoristas d ON d.id = mt.driver_id
         WHERE mt.monitor_id = %s AND mt.ativo = TRUE
         ORDER BY device_id
    """, (monitor_id,))

    vehicles = cursor.fetchall()

    # Convert datetime to ISO format
    for vehicle in vehicles:
        if vehicle['atribuido_em']:
            vehicle['atribuido_em'] = vehicle['atribuido_em'].isoformat()

    cursor.close()
    conn.close()

    return vehicles


def get_monitor_vehicles_unified(monitor_id: int) -> List[Dict]:
    """
    Lista veículos de um monitor com dados UNIFICADOS (tracker + dirijabem)
    Retorna informações de ambas as fontes quando disponível
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Buscar veículos do monitor com JOIN na tabela unificada
    cursor.execute("""
        SELECT
            mt.id AS veiculomonitor_id,
            mt.monitor_id,
            mt.legacy_device_id AS device_id,
            mt.ativo,
            mt.vehicle_id AS veiculo_unificado_id,
            v.placa,
            CASE mt.target_type WHEN 'vehicle' THEN 'tracker_only' ELSE 'app_only' END AS fonte,
            COALESCE(v.descricao, d.nome) AS descricao,
            (SELECT vi.valor_externo
               FROM monitoramento.veiculo_identidades vi
              WHERE vi.vehicle_id = mt.vehicle_id
                AND vi.fonte_codigo = 'tracker'
                AND vi.tipo_identidade = 'device_id' AND vi.ativo = TRUE
              ORDER BY vi.principal DESC, vi.id LIMIT 1) AS vu_device_id,
            (SELECT CAST(mi.valor_externo AS UNSIGNED)
               FROM monitoramento.motorista_identidades mi
              WHERE mi.driver_id = mt.driver_id
                AND mi.fonte_codigo = 'dirijabem'
                AND mi.tipo_identidade = 'user_id' AND mi.ativo = TRUE
              LIMIT 1) AS codusu
          FROM monitoramento.monitor_targets mt
     LEFT JOIN monitoramento.veiculos v ON v.id = mt.vehicle_id
     LEFT JOIN monitoramento.motoristas d ON d.id = mt.driver_id
         WHERE mt.monitor_id = %s AND mt.ativo = TRUE
         ORDER BY v.placa, d.nome
    """, (monitor_id,))

    vehicles = cursor.fetchall()
    cursor.close()
    conn.close()

    return vehicles


def get_all_unified_vehicles() -> List[Dict]:
    """
    Retorna TODOS os veículos unificados disponíveis para monitoramento
    """
    # Import local evita ciclo: identity_db reutiliza get_connection deste módulo.
    from .identity_db import get_unified_vehicle_records

    return get_unified_vehicle_records()


def add_vehicle_to_monitor(monitor_id: int, veicod: int, device_id: str) -> int:
    """Adiciona veículo ao monitor"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT vehicle_id
          FROM monitoramento.veiculo_identidades
         WHERE fonte_codigo = 'tracker' AND ativo = TRUE
           AND ((tipo_identidade = 'device_id' AND valor_externo = %s)
             OR (tipo_identidade = 'vehicle_id' AND valor_externo = %s))
         ORDER BY tipo_identidade = 'device_id' DESC
         LIMIT 1
    """, (device_id, str(veicod)))
    identity = cursor.fetchone()
    if not identity:
        cursor.close()
        conn.close()
        raise ValueError('Veículo canônico Tracker não encontrado')
    cursor.execute("""
        INSERT INTO monitoramento.monitor_targets
            (monitor_id, target_type, vehicle_id, fonte_codigo,
             legacy_veicod_tracker, legacy_device_id, ativo)
        VALUES (%s, 'vehicle', %s, 'tracker', %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), ativo = TRUE,
          legacy_veicod_tracker = VALUES(legacy_veicod_tracker),
          legacy_device_id = VALUES(legacy_device_id)
    """, (monitor_id, identity['vehicle_id'], veicod, device_id))

    veiculomonitor_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return veiculomonitor_id


def remove_vehicle_from_monitor(veiculomonitor_id: int) -> bool:
    """Remove veículo do monitor (soft delete)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE monitoramento.monitor_targets SET ativo = FALSE WHERE id = %s
    """, (veiculomonitor_id,))

    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()

    return success


# ==================== Análises ====================

def save_analysis(monitor_id: int, veiculomonitor_id: int, data: Dict) -> int:
    """Salva análise no banco"""
    conn = get_connection()
    cursor = conn.cursor()

    eventos_por_tipo_json = json.dumps(data.get('eventos_por_tipo', {}))

    cursor.execute("""
        INSERT INTO monitoramento.monitor_analises (monitor_id, monitor_target_id, periodo_inicio, periodo_fim,
                                     total_eventos, score_inicial, score_final, eventos_por_tipo,
                                     conclusao, severidade)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        monitor_id,
        veiculomonitor_id,
        data.get('periodo_inicio'),
        data.get('periodo_fim'),
        data.get('total_eventos', 0),
        data.get('score_inicial'),
        data.get('score_final'),
        eventos_por_tipo_json,
        data.get('conclusao'),
        data.get('severidade')
    ))

    analysis_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return analysis_id


def get_monitor_analyses(monitor_id: int, limit: int = 50) -> List[Dict]:
    """Lista análises de um monitor"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT ma.*, ma.monitor_target_id AS veiculomonitor_id,
               COALESCE(mt.legacy_device_id,
                 (SELECT vi.valor_externo FROM monitoramento.veiculo_identidades vi
                   WHERE vi.vehicle_id = mt.vehicle_id
                     AND vi.fonte_codigo = 'tracker'
                     AND vi.tipo_identidade = 'device_id' AND vi.ativo = TRUE
                   LIMIT 1)) AS device_id
        FROM monitoramento.monitor_analises ma
        JOIN monitoramento.monitor_targets mt ON ma.monitor_target_id = mt.id
        WHERE ma.monitor_id = %s
        ORDER BY ma.analisado_em DESC
        LIMIT %s
    """, (monitor_id, limit))

    analyses = cursor.fetchall()

    # Convert datetime and JSON
    for analysis in analyses:
        if analysis['analisado_em']:
            analysis['analisado_em'] = analysis['analisado_em'].isoformat()
        if analysis['periodo_inicio']:
            analysis['periodo_inicio'] = analysis['periodo_inicio'].isoformat()
        if analysis['periodo_fim']:
            analysis['periodo_fim'] = analysis['periodo_fim'].isoformat()
        if analysis['eventos_por_tipo']:
            analysis['eventos_por_tipo'] = json.loads(analysis['eventos_por_tipo'])

    cursor.close()
    conn.close()

    return analyses


# ==================== Alertas ====================

def create_alert(data: Dict) -> int:
    """Cria novo alerta"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO monitoramento.monitor_alertas (analise_id, monitor_id, monitor_target_id, device_id,
                                    nome_motorista, titulo, mensagem, severidade, tipo,
                                    total_eventos_relacionados)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data.get('analise_id'),
        data.get('monitor_id'),
        data.get('veiculomonitor_id'),
        data.get('device_id'),
        data.get('nome_motorista'),
        data.get('titulo'),
        data.get('mensagem'),
        data.get('severidade'),
        data.get('tipo', 'behavior'),
        data.get('total_eventos_relacionados', 0)
    ))

    alert_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return alert_id


def get_alerts(filters: Dict = None) -> List[Dict]:
    """Lista alertas com filtros opcionais"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = "SELECT ma.*, ma.monitor_target_id AS veiculomonitor_id FROM monitoramento.monitor_alertas ma WHERE 1=1"
    params = []

    if filters:
        if 'status' in filters:
            sql += " AND status = %s"
            params.append(filters['status'])
        if 'severidade' in filters:
            sql += " AND severidade = %s"
            params.append(filters['severidade'])
        if 'monitor_id' in filters:
            sql += " AND monitor_id = %s"
            params.append(filters['monitor_id'])

    sql += " ORDER BY criado_em DESC LIMIT 100"

    cursor.execute(sql, params)
    alerts = cursor.fetchall()

    # Convert datetime
    for alert in alerts:
        if alert['criado_em']:
            alert['criado_em'] = alert['criado_em'].isoformat()
        if alert['reconhecido_em']:
            alert['reconhecido_em'] = alert['reconhecido_em'].isoformat()

    cursor.close()
    conn.close()

    return alerts


def get_alert_by_id(alert_id: int) -> Optional[Dict]:
    """Retorna alerta por ID"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT ma.*, ma.monitor_target_id AS veiculomonitor_id "
        "FROM monitoramento.monitor_alertas ma WHERE id = %s",
        (alert_id,),
    )
    alert = cursor.fetchone()

    if alert:
        if alert['criado_em']:
            alert['criado_em'] = alert['criado_em'].isoformat()
        if alert['reconhecido_em']:
            alert['reconhecido_em'] = alert['reconhecido_em'].isoformat()

    cursor.close()
    conn.close()

    return alert


def acknowledge_alert(alert_id: int, reconhecido_por: str) -> bool:
    """Marca alerta como reconhecido"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE monitoramento.monitor_alertas
        SET status = 'acknowledged', reconhecido_em = NOW(), reconhecido_por = %s
        WHERE id = %s
    """, (reconhecido_por, alert_id))

    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()

    return success


def resolve_alert(alert_id: int) -> bool:
    """Marca alerta como resolvido"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE monitoramento.monitor_alertas SET status = 'resolved' WHERE id = %s
    """, (alert_id,))

    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()

    return success


def dismiss_alert(alert_id: int) -> bool:
    """Marca alerta como descartado"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE monitoramento.monitor_alertas SET status = 'dismissed' WHERE id = %s
    """, (alert_id,))

    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()

    return success


# ==================== Estatísticas ====================

def get_alert_stats() -> Dict:
    """Retorna estatísticas de alertas"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'acknowledged' THEN 1 ELSE 0 END) as acknowledged,
            SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN status = 'dismissed' THEN 1 ELSE 0 END) as dismissed,
            SUM(CASE WHEN severidade = 'critical' THEN 1 ELSE 0 END) as critical,
            SUM(CASE WHEN severidade = 'high' THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN severidade = 'medium' THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN severidade = 'low' THEN 1 ELSE 0 END) as low
        FROM monitoramento.monitor_alertas
    """)

    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    return stats or {}


def get_monitor_stats() -> Dict:
    """Retorna estatísticas gerais dos monitores"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) as total_monitores,
            SUM(CASE WHEN ativo = TRUE THEN 1 ELSE 0 END) as ativos,
            (SELECT COUNT(*) FROM monitoramento.monitor_targets WHERE ativo = TRUE) as total_veiculos,
            (SELECT COUNT(*) FROM monitoramento.monitor_analises) as total_analises,
            (SELECT COUNT(*) FROM monitoramento.monitor_alertas WHERE status = 'pending') as alertas_pendentes
        FROM monitoramento.monitores
    """)

    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    return stats or {}
