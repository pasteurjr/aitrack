"""
API Validator - Testa todos os endpoints do sistema de monitores
Gera relatório em Markdown com screenshots
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Tuple
import os

API_BASE = "http://localhost:5009/api"
REPORT_DIR = "tests/reports"
SCREENSHOTS_DIR = f"{REPORT_DIR}/screenshots"

class APIValidator:
    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

        # Criar diretórios se não existirem
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    def test_endpoint(self, method: str, endpoint: str, name: str,
                     expected_status: int = 200, data: Dict = None) -> Tuple[bool, Dict]:
        """
        Testa um endpoint da API

        Returns:
            (success, response_data)
        """
        self.total_tests += 1
        url = f"{API_BASE}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=5)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=5)
            elif method == "DELETE":
                response = requests.delete(url, timeout=5)
            else:
                raise ValueError(f"Método HTTP inválido: {method}")

            success = response.status_code == expected_status

            if success:
                self.passed_tests += 1
                status = "✅ PASS"
            else:
                self.failed_tests += 1
                status = "❌ FAIL"

            result = {
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "expected_code": expected_status,
                "actual_code": response.status_code,
                "response": response.json() if response.content else {},
                "success": success
            }

            self.results.append(result)
            return success, result

        except Exception as e:
            self.failed_tests += 1
            result = {
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "status": "❌ ERROR",
                "error": str(e),
                "success": False
            }
            self.results.append(result)
            return False, result

    def run_all_tests(self):
        """Executa todos os testes de validação"""
        print("🧪 Iniciando validação da API...")
        print("=" * 80)

        # MONITORS
        print("\n📊 Testando endpoints de MONITORS...")
        self.test_endpoint("GET", "/monitors", "Listar todos os monitores")
        self.test_endpoint("GET", "/monitors/1", "Buscar monitor #1")
        self.test_endpoint("GET", "/monitors/999", "Buscar monitor inexistente", expected_status=404)
        self.test_endpoint("GET", "/monitors/stats", "Estatísticas de monitores")

        # MONITORS - VEHICLES
        print("\n🚗 Testando endpoints de VEHICLES...")
        self.test_endpoint("GET", "/monitors/1/vehicles", "Listar veículos do monitor #1")
        self.test_endpoint("GET", "/monitors/2/vehicles", "Listar veículos do monitor #2")

        # MONITORS - ANALYSES
        print("\n📈 Testando endpoints de ANALYSES...")
        self.test_endpoint("GET", "/monitors/1/analyses", "Listar análises do monitor #1")
        self.test_endpoint("GET", "/monitors/1/analyses?limit=10", "Listar análises com limite")

        # ALERTS
        print("\n🔔 Testando endpoints de ALERTS...")
        self.test_endpoint("GET", "/alerts", "Listar todos os alertas")
        self.test_endpoint("GET", "/alerts?status=pending", "Listar alertas pendentes")
        self.test_endpoint("GET", "/alerts?severidade=critical", "Listar alertas críticos")
        self.test_endpoint("GET", "/alerts/stats", "Estatísticas de alertas")

        # Testar um alerta específico (se existir)
        success, result = self.test_endpoint("GET", "/alerts", "Buscar alertas para teste")
        if success and result['response']:
            alert_id = result['response'][0]['id']
            self.test_endpoint("GET", f"/alerts/{alert_id}", f"Buscar alerta #{alert_id}")

        # EVENTS
        print("\n📋 Testando endpoints de EVENTS...")
        self.test_endpoint("GET", "/events/catalog", "Catálogo de tipos de eventos")
        self.test_endpoint("GET", "/events?limit=10", "Listar eventos (limite 10)")
        self.test_endpoint("GET", "/events?device_id=SIM-1000", "Listar eventos do SIM-1000")
        self.test_endpoint("GET", "/events/stats", "Estatísticas de eventos")

        # FLEET (Behavioral Engine)
        print("\n🚙 Testando endpoints de FLEET...")
        self.test_endpoint("GET", "/fleet/scores", "Scores de todos os veículos")
        self.test_endpoint("GET", "/fleet/events?limit=20", "Eventos comportamentais")
        self.test_endpoint("GET", "/fleet/stats", "Estatísticas da frota")
        self.test_endpoint("GET", "/vehicles/SIM-1000/score", "Score do veículo SIM-1000")

        print("\n" + "=" * 80)
        print(f"✅ Testes concluídos: {self.passed_tests}/{self.total_tests} passaram")
        print(f"❌ Falhas: {self.failed_tests}")
        print("=" * 80)

    def generate_markdown_report(self) -> str:
        """Gera relatório em Markdown"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md = f"""# 🧪 Relatório de Validação - API AITrack Monitor System

**Data:** {timestamp}
**Total de Testes:** {self.total_tests}
**Passaram:** ✅ {self.passed_tests}
**Falharam:** ❌ {self.failed_tests}
**Taxa de Sucesso:** {(self.passed_tests/self.total_tests*100):.1f}%

---

## 📊 Resumo por Categoria

"""

        # Agrupar por categoria
        categories = {
            "MONITORS": [],
            "VEHICLES": [],
            "ANALYSES": [],
            "ALERTS": [],
            "EVENTS": [],
            "FLEET": []
        }

        for result in self.results:
            endpoint = result['endpoint']
            if '/monitors' in endpoint and '/vehicles' not in endpoint and '/analyses' not in endpoint:
                categories['MONITORS'].append(result)
            elif '/vehicles' in endpoint:
                categories['VEHICLES'].append(result)
            elif '/analyses' in endpoint:
                categories['ANALYSES'].append(result)
            elif '/alerts' in endpoint:
                categories['ALERTS'].append(result)
            elif '/events' in endpoint:
                categories['EVENTS'].append(result)
            elif '/fleet' in endpoint or '/vehicles/' in endpoint:
                categories['FLEET'].append(result)

        for category, tests in categories.items():
            if not tests:
                continue

            passed = sum(1 for t in tests if t['success'])
            total = len(tests)

            md += f"\n### {category}\n"
            md += f"**Status:** {passed}/{total} testes passaram\n\n"
            md += "| Status | Método | Endpoint | Nome |\n"
            md += "|--------|--------|----------|------|\n"

            for test in tests:
                md += f"| {test['status']} | `{test['method']}` | `{test['endpoint']}` | {test['name']} |\n"

        md += "\n---\n\n## 📋 Detalhes dos Testes\n\n"

        for i, result in enumerate(self.results, 1):
            md += f"\n### {i}. {result['name']}\n\n"
            md += f"**Método:** `{result['method']}`  \n"
            md += f"**Endpoint:** `{result['endpoint']}`  \n"
            md += f"**Status:** {result['status']}  \n"

            if 'expected_code' in result:
                md += f"**Código Esperado:** {result['expected_code']}  \n"
                md += f"**Código Recebido:** {result['actual_code']}  \n"

            if 'error' in result:
                md += f"\n**Erro:**\n```\n{result['error']}\n```\n"
            elif 'response' in result:
                # Limitar tamanho da resposta
                response_str = json.dumps(result['response'], indent=2, ensure_ascii=False)
                if len(response_str) > 1000:
                    response_str = response_str[:1000] + "\n... (truncado)"

                md += f"\n**Resposta:**\n```json\n{response_str}\n```\n"

        md += "\n---\n\n## 📊 Estatísticas Finais\n\n"
        md += f"- **Total de Endpoints Testados:** {self.total_tests}\n"
        md += f"- **Sucessos:** ✅ {self.passed_tests}\n"
        md += f"- **Falhas:** ❌ {self.failed_tests}\n"
        md += f"- **Taxa de Sucesso:** {(self.passed_tests/self.total_tests*100):.1f}%\n"

        if self.failed_tests == 0:
            md += "\n### 🎉 Todos os testes passaram!\n\n"
            md += "A API está funcionando perfeitamente. Todos os endpoints responderam conforme esperado.\n"
        else:
            md += f"\n### ⚠️ {self.failed_tests} teste(s) falharam\n\n"
            md += "Verifique os detalhes acima para identificar e corrigir os problemas.\n"

        md += f"\n---\n\n*Relatório gerado automaticamente em {timestamp}*\n"

        return md

    def save_report(self, filename: str = None):
        """Salva o relatório em arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{REPORT_DIR}/validation_report_{timestamp}.md"

        md = self.generate_markdown_report()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"\n📄 Relatório salvo em: {filename}")
        return filename


if __name__ == "__main__":
    validator = APIValidator()
    validator.run_all_tests()
    validator.save_report()
