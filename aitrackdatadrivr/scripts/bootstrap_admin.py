"""Cria explicitamente o primeiro usuário; não possui senha padrão."""

import os

from server.auth_service import create_user


def main():
    email = os.environ.get('AITRACK_BOOTSTRAP_ADMIN_EMAIL')
    password = os.environ.get('AITRACK_BOOTSTRAP_ADMIN_PASSWORD')
    name = os.environ.get('AITRACK_BOOTSTRAP_ADMIN_NAME', 'Administrador')
    tenant = os.environ.get('AITRACK_BOOTSTRAP_TENANT', 'default')
    if not email or not password:
        raise SystemExit('Defina AITRACK_BOOTSTRAP_ADMIN_EMAIL e AITRACK_BOOTSTRAP_ADMIN_PASSWORD')
    result = create_user(email, name, password, tenant)
    print(f"Usuário criado: {result['public_id']} (tenant_id={result['tenant_id']})")


if __name__ == '__main__':
    main()
