#!/usr/bin/env python3
"""
Script Principal de Validação
Executa testes de API e captura screenshots
"""

import sys
import os
import asyncio
from datetime import datetime

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.api_validator import APIValidator
from tests.playwright_validator import PlaywrightValidator


def print_banner():
    """Imprime banner inicial"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║        🧪 AITrack Monitor System - Validação Automática                 ║
║                                                                          ║
║        Testa todos os endpoints da API e gera relatório completo        ║
║        com capturas de tela                                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


def check_server():
    """Verifica se o servidor está rodando"""
    import requests
    try:
        response = requests.get("http://localhost:5009/api/test", timeout=2)
        return True
    except:
        return False


async def main():
    print_banner()

    # Verificar se servidor está rodando
    print("🔍 Verificando se o servidor está rodando...")
    if not check_server():
        print("❌ ERRO: Servidor não está rodando!")
        print("\n💡 Para iniciar o servidor, execute:")
        print("   python run.py")
        print("\nEm outro terminal, execute:")
        print("   python tests/run_validation.py")
        return

    print("✅ Servidor está rodando!\n")

    # Criar diretório de relatórios
    os.makedirs("tests/reports", exist_ok=True)
    os.makedirs("tests/reports/screenshots", exist_ok=True)

    # PARTE 1: Testes de API
    print("\n" + "="*80)
    print("PARTE 1: TESTES DE ENDPOINTS")
    print("="*80 + "\n")

    validator = APIValidator()
    validator.run_all_tests()
    api_report = validator.save_report()

    # PARTE 2: Capturas de Tela
    print("\n" + "="*80)
    print("PARTE 2: CAPTURAS DE TELA")
    print("="*80 + "\n")

    try:
        playwright_validator = PlaywrightValidator()
        await playwright_validator.run_all_captures()
        visual_report = playwright_validator.generate_report_with_images()
    except Exception as e:
        print(f"⚠️  Não foi possível capturar screenshots: {e}")
        print("💡 Certifique-se de que Playwright está instalado:")
        print("   pip install playwright")
        print("   playwright install chromium")
        visual_report = None

    # PARTE 3: Relatório Consolidado
    print("\n" + "="*80)
    print("PARTE 3: RELATÓRIO CONSOLIDADO")
    print("="*80 + "\n")

    consolidate_reports(validator, api_report, visual_report)

    print("\n✅ VALIDAÇÃO COMPLETA!")
    print("=" * 80)


def consolidate_reports(validator, api_report, visual_report):
    """Cria um relatório consolidado final"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = f"""# 🎯 Relatório Consolidado - AITrack Monitor System

**Data da Validação:** {timestamp}

---

## 📊 Resumo Executivo

### Estatísticas Gerais

| Métrica | Valor |
|---------|-------|
| **Total de Testes** | {validator.total_tests} |
| **Testes Passaram** | ✅ {validator.passed_tests} |
| **Testes Falharam** | ❌ {validator.failed_tests} |
| **Taxa de Sucesso** | {(validator.passed_tests/validator.total_tests*100):.1f}% |

### Status Geral

"""

    if validator.failed_tests == 0:
        md += """
✅ **TODOS OS TESTES PASSARAM!**

O sistema está funcionando perfeitamente. Todos os endpoints da API estão respondendo conforme esperado.

### Endpoints Validados

Foram testados **{total}** endpoints diferentes, incluindo:

- **Monitores:** Criação, listagem, atualização e estatísticas
- **Veículos:** Associação com monitores e busca de dados
- **Alertas:** Listagem, filtragem, reconhecimento e estatísticas
- **Eventos:** Catálogo, histórico e estatísticas
- **Frota:** Scores comportamentais e eventos em tempo real

""".format(total=validator.total_tests)
    else:
        md += f"""
⚠️ **{validator.failed_tests} TESTE(S) FALHARAM**

Alguns endpoints não estão funcionando conforme esperado. Verifique os detalhes nos relatórios específicos.

"""

    md += """
---

## 📋 Relatórios Detalhados

### 1. Relatório de Testes de API

Contém todos os detalhes dos testes executados, incluindo requisições, respostas e códigos de status.

"""

    if api_report:
        md += f"📄 **[Ver Relatório de API]({os.path.basename(api_report)})**\n\n"

    md += """
### 2. Relatório Visual com Screenshots

Capturas de tela das respostas da API em formato visual.

"""

    if visual_report:
        md += f"📸 **[Ver Relatório Visual]({os.path.basename(visual_report)})**\n\n"
    else:
        md += "⚠️ Relatório visual não foi gerado (Playwright não instalado)\n\n"

    md += """
---

## 🚀 Próximos Passos

### Se todos os testes passaram:

1. ✅ Sistema está pronto para uso
2. ✅ Pode iniciar testes de integração
3. ✅ Pode começar a desenvolver o frontend

### Se houve falhas:

1. ❌ Verifique se o servidor está rodando: `python run.py`
2. ❌ Verifique se o banco de dados está acessível
3. ❌ Consulte os logs de erro nos relatórios detalhados

---

## 📁 Estrutura de Arquivos

```
tests/
├── api_validator.py          # Script de testes de API
├── playwright_validator.py   # Script de capturas de tela
├── run_validation.py          # Script principal (este arquivo)
└── reports/
    ├── validation_report_*.md # Relatório de testes
    ├── visual_report_*.md     # Relatório visual
    ├── CONSOLIDATED_REPORT.md # Este relatório
    └── screenshots/           # Capturas de tela
        ├── _monitors.png
        ├── _alerts.png
        └── ...
```

---

## 🛠️ Como Executar a Validação

```bash
# 1. Certifique-se de que o servidor está rodando
python run.py

# 2. Em outro terminal, execute a validação
python tests/run_validation.py

# 3. Os relatórios serão gerados em tests/reports/
```

---

*Relatório consolidado gerado automaticamente em {timestamp}*
"""

    # Salvar relatório consolidado
    consolidated_path = "tests/reports/CONSOLIDATED_REPORT.md"
    with open(consolidated_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"📄 Relatório consolidado salvo em: {consolidated_path}")


if __name__ == "__main__":
    asyncio.run(main())
