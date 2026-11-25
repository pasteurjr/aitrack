"""Tenant ativo derivado exclusivamente da sessão autenticada."""

from flask import g, has_request_context


class TenantContextMissing(RuntimeError):
    pass


def current_tenant_id(*, required=True):
    principal = getattr(g, 'auth', None) if has_request_context() else None
    tenant_id = principal.get('tenant_id') if principal else None
    if required and not tenant_id:
        raise TenantContextMissing('Tenant autenticado obrigatório')
    return tenant_id


def trusted_actor():
    principal = getattr(g, 'auth', None) if has_request_context() else None
    if not principal:
        raise TenantContextMissing('Principal autenticado obrigatório')
    return {
        'type': 'human',
        'id': principal['user_public_id'],
        'name': principal['display_name'],
    }
