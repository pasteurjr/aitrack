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
               (SELECT COUNT(*) FROM veiculomonitor WHERE monitor_id = monitores.id AND ativo = TRUE) as veiculos_monitorados
        FROM monitores
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
               (SELECT COUNT(*) FROM veiculomonitor WHERE monitor_id = monitores.id AND ativo = TRUE) as veiculos_monitorados
        FROM monitores
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
        FROM monitores
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
        INSERT INTO monitores (nome, descricao, tipo_monitor, intervalo_analise, janela_contexto,
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
    sql = f"UPDATE monitores SET {', '.join(fields)} WHERE id = %s"

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
        SELECT vm.id, vm.monitor_id, vm.tipo_veiculo, vm.veicod_tracker,
               vm.codusu_dirijabem, vm.device_id, vm.ativo, vm.atribuido_em,
               v.VEIPLACA as placa
        FROM veiculomonitor vm
        LEFT JOIN veiculos v ON vm.veicod_tracker = v.VEICOD
        WHERE vm.monitor_id = %s AND vm.ativo = TRUE
        ORDER BY vm.device_id
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
            vm.id as veiculomonitor_id,
            vm.monitor_id,
            vm.device_id,
            vm.ativo,
            vu.id as veiculo_unificado_id,
            vu.placa,
            vu.tipo as fonte,
            vu.descricao,
            vu.device_id as vu_device_id,
            vu.codusu
        FROM veiculomonitor vm
        LEFT JOIN veiculo_unificado vu ON (
            vm.device_id = vu.device_id OR
            vm.codusu_dirijabem = vu.codusu
        )
        WHERE vm.monitor_id = %s AND vm.ativo = TRUE
        ORDER BY vu.placa
    """, (monitor_id,))

    vehicles = cursor.fetchall()
    cursor.close()
    conn.close()

    return vehicles


def get_all_unified_vehicles() -> List[Dict]:
    """
    Retorna TODOS os veículos unificados disponíveis para monitoramento
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            device_id,
            codusu,
            placa,
            tipo,
            descricao,
            ativo
        FROM veiculo_unificado
        WHERE ativo = TRUE
        ORDER BY placa
    """)

    vehicles = cursor.fetchall()
    cursor.close()
    conn.close()

    return vehicles


def add_vehicle_to_monitor(monitor_id: int, veicod: int, device_id: str) -> int:
    """Adiciona veículo ao monitor"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO veiculomonitor (monitor_id, tipo_veiculo, veicod_tracker, device_id)
        VALUES (%s, 'tracker', %s, %s)
    """, (monitor_id, veicod, device_id))

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
        UPDATE veiculomonitor SET ativo = FALSE WHERE id = %s
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
        INSERT INTO monitor_analises (monitor_id, veiculomonitor_id, periodo_inicio, periodo_fim,
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
        SELECT ma.*, vm.device_id
        FROM monitor_analises ma
        JOIN veiculomonitor vm ON ma.veiculomonitor_id = vm.id
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
        INSERT INTO monitor_alertas (analise_id, monitor_id, veiculomonitor_id, device_id,
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

    sql = "SELECT * FROM monitor_alertas WHERE 1=1"
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

    cursor.execute("SELECT * FROM monitor_alertas WHERE id = %s", (alert_id,))
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
        UPDATE monitor_alertas
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
        UPDATE monitor_alertas SET status = 'resolved' WHERE id = %s
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
        UPDATE monitor_alertas SET status = 'dismissed' WHERE id = %s
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
        FROM monitor_alertas
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
            (SELECT COUNT(*) FROM veiculomonitor WHERE ativo = TRUE) as total_veiculos,
            (SELECT COUNT(*) FROM monitor_analises) as total_analises,
            (SELECT COUNT(*) FROM monitor_alertas WHERE status = 'pending') as alertas_pendentes
        FROM monitores
    """)

    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    return stats or {}
