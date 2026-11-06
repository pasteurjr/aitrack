# Validações da Etapa 3

## UI-3.0A — Modelo operacional unificado

**Data:** 06/11/2026

**Commit:** `e52da8e`

- Definido `monitoramento` como schema operacional comum.
- Separadas identidades de veículos e motoristas. `CODUSU` do Dirija Bem passa
  a ser identidade de motorista, não identidade de veículo.
- Tracker e Dirija Bem permanecem sistemas-fonte e não recebem FKs da camada
  operacional.
- Migration 010 coberta por quatro testes estruturais.
- Regressão antes da aplicação: `103 passed, 3 skipped`.

## UI-3.0B — Runner e implantação inicial

**Data:** 06/11/2026

**Checkpoint anterior:** `e52da8e`

### Segurança do runner

- Descoberta determinística das migrations por número e nome.
- Baseline 001–009 só é registrado depois da confirmação das tabelas e colunas
  existentes no banco.
- Nome e SHA-256 de cada arquivo aplicado ficam em
  `tracker.schema_migrations`; alteração posterior de migration aplicada causa
  erro explícito.
- O cliente MariaDB recebe credenciais por arquivo temporário com modo `0600`,
  removido mesmo em caso de falha; a senha não aparece na linha de comando.
- `--dry-run` não cria tabela nem registra baseline.

### Aplicação e evidências

- Servidor confirmado: MariaDB `10.3.39`.
- A migration `010_create_unified_operational_identity.sql` foi aplicada com
  sucesso.
- `monitoramento` possui seis tabelas: fontes, veículos, identidades de veículo,
  motoristas, identidades de motorista e vínculos temporais.
- Fontes `tracker` e `dirijabem` cadastradas como somente leitura.
- Dez arquivos registrados no histórico: baseline legado mais migration 010.
- Segunda execução em dry-run: `0 migrations pendentes`.
- Regressão posterior: `108 passed, 3 skipped`.
- Nenhuma cópia de dados ou mudança nas APIs ocorreu nesta etapa; as tabelas de
  identidade permanecem vazias até a UI-3.0C.
