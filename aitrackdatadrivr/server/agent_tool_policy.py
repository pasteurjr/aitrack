"""Allowlist por versão; ausência de política sempre nega."""

from dataclasses import dataclass
import json
from typing import Dict

from .agent_read_tools import TOOL_NAMES, ToolDenied, ToolScope
from .monitor_db import get_connection


CONSTRAINT_FIELDS = {'allowed_arguments', 'allowed_sources', 'max_limit'}


@dataclass(frozen=True)
class ToolPermission:
    policy_id: int
    tool_name: str
    allowed_arguments: tuple[str, ...]
    allowed_sources: tuple[str, ...]
    max_limit: int


class ToolPolicySet:
    def __init__(self, config_version_id: int, permissions: Dict[str, ToolPermission]):
        self.config_version_id = config_version_id
        self.permissions = permissions

    def authorize(self, tool_name: str, arguments: Dict, scope: ToolScope) -> ToolPermission:
        permission = self.permissions.get(tool_name)
        if not permission:
            raise ToolDenied(f'Ferramenta {tool_name} ausente da allowlist da versão')
        extra = set(arguments) - set(permission.allowed_arguments)
        if extra:
            raise ToolDenied(f'Parâmetros fora da política: {sorted(extra)}')
        if not set(scope.source_codes) <= set(permission.allowed_sources):
            raise ToolDenied('Fonte fora da política da ferramenta')
        default_limit = (
            scope.max_history_points
            if tool_name in {'position.history', 'geofence.list_for_vehicle'}
            else 1
        )
        limit = arguments.get('limit', default_limit)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit > permission.max_limit:
            raise ToolDenied('limit excede política da ferramenta')
        return permission


def validate_constraints(tool_name: str, value: Dict) -> Dict:
    if tool_name not in TOOL_NAMES:
        raise ValueError('tool_name não pertence à registry somente leitura')
    if not isinstance(value, dict) or set(value) != CONSTRAINT_FIELDS:
        raise ValueError(f'constraints deve conter exatamente {sorted(CONSTRAINT_FIELDS)}')
    arguments, sources, max_limit = (
        value['allowed_arguments'], value['allowed_sources'], value['max_limit'],
    )
    if not isinstance(arguments, list) or 'vehicle_id' not in arguments or not set(arguments) <= {'vehicle_id','limit'}:
        raise ValueError('allowed_arguments inválido')
    if not isinstance(sources, list) or not sources or not set(sources) <= {'tracker','dirijabem'}:
        raise ValueError('allowed_sources inválido')
    if not isinstance(max_limit, int) or isinstance(max_limit, bool) or not 1 <= max_limit <= 500:
        raise ValueError('max_limit deve estar entre 1 e 500')
    return {
        'allowed_arguments': sorted(set(arguments)),
        'allowed_sources': sorted(set(sources)),
        'max_limit': max_limit,
    }


def load_tool_policy(config_version_id: int) -> ToolPolicySet:
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id,tool_name,constraints_json FROM monitoramento.agent_tool_policies "
            "WHERE config_version_id=%s ORDER BY id",
            (config_version_id,),
        )
        permissions={}
        for row in cursor.fetchall():
            value=validate_constraints(row['tool_name'],json.loads(row['constraints_json']))
            permissions[row['tool_name']]=ToolPermission(
                row['id'],row['tool_name'],tuple(value['allowed_arguments']),
                tuple(value['allowed_sources']),value['max_limit'],
            )
        return ToolPolicySet(config_version_id,permissions)
    finally:cursor.close();conn.close()


def add_tool_policy(config_version_id: int, tool_name: str, constraints: Dict,
                    actor: str, reason: str) -> int:
    value=validate_constraints(tool_name,constraints)
    actor,reason=str(actor or '').strip(),str(reason or '').strip()
    if not actor or len(reason)<5:raise ValueError('actor e reason são obrigatórios')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute(
            "SELECT status FROM monitoramento.agent_config_versions WHERE id=%s FOR UPDATE",
            (config_version_id,),
        );config=cursor.fetchone()
        if not config:raise LookupError('Configuração não encontrada')
        if config['status']!='draft':raise ValueError('Políticas só podem ser adicionadas a draft')
        cursor.execute(
            "INSERT INTO monitoramento.agent_tool_policies "
            "(config_version_id,tool_name,constraints_json,created_by,change_reason) "
            "VALUES(%s,%s,%s,%s,%s)",
            (config_version_id,tool_name,json.dumps(value,separators=(',',':'),sort_keys=True),actor,reason),
        );policy_id=cursor.lastrowid;conn.commit();return policy_id
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()
