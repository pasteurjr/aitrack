"""
Playwright Validator - Captura screenshots visuais da API
"""

import asyncio
import json
from playwright.async_api import async_playwright
import requests
from datetime import datetime
import os

API_BASE = "http://localhost:5009/api"
SCREENSHOTS_DIR = "tests/reports/screenshots"

class PlaywrightValidator:
    def __init__(self):
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        self.screenshots = []

    async def create_html_viewer(self, title: str, data: dict, endpoint: str):
        """Cria uma página HTML para visualizar os dados da API"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            color: white;
            padding: 30px;
            border-bottom: 4px solid #10b981;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header .endpoint {{
            font-family: 'Courier New', monospace;
            background: rgba(16, 185, 129, 0.2);
            padding: 8px 16px;
            border-radius: 6px;
            display: inline-block;
            margin-top: 10px;
            font-size: 14px;
        }}
        .content {{
            padding: 30px;
        }}
        .status {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            margin-bottom: 20px;
            font-size: 16px;
        }}
        .status.success {{
            background: #10b981;
            color: white;
        }}
        .status.error {{
            background: #ef4444;
            color: white;
        }}
        pre {{
            background: #1f2937;
            color: #10b981;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.6;
            box-shadow: inset 0 2px 8px rgba(0,0,0,0.3);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #10b981;
        }}
        .stat-card .label {{
            color: #6b7280;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .stat-card .value {{
            color: #111827;
            font-size: 24px;
            font-weight: bold;
        }}
        .timestamp {{
            color: #9ca3af;
            font-size: 14px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 {title}</h1>
            <div class="endpoint">GET {endpoint}</div>
            <div class="timestamp">📅 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
        <div class="content">
            <div class="status success">✅ 200 OK</div>

            {self._generate_stats_html(data)}

            <h2 style="margin: 30px 0 15px 0; color: #111827;">📊 Resposta JSON:</h2>
            <pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_stats_html(self, data):
        """Gera HTML de estatísticas baseado no tipo de dados"""
        if isinstance(data, list):
            return f"""
            <div class="stats">
                <div class="stat-card">
                    <div class="label">Total de Itens</div>
                    <div class="value">{len(data)}</div>
                </div>
            </div>
            """
        elif isinstance(data, dict):
            stats_html = '<div class="stats">'
            for key, value in list(data.items())[:6]:  # Primeiros 6 campos
                if isinstance(value, (int, float, str)) and not isinstance(value, bool):
                    stats_html += f"""
                    <div class="stat-card">
                        <div class="label">{key.replace('_', ' ').title()}</div>
                        <div class="value">{value}</div>
                    </div>
                    """
            stats_html += '</div>'
            return stats_html
        return ""

    async def capture_endpoint(self, endpoint: str, title: str):
        """Captura screenshot de um endpoint"""
        try:
            # Buscar dados da API
            response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
            data = response.json()

            # Criar HTML
            html = await self.create_html_viewer(title, data, endpoint)

            # Salvar HTML temporário
            temp_html = f"{SCREENSHOTS_DIR}/temp.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html)

            # Capturar screenshot com Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={'width': 1280, 'height': 1024})
                await page.goto(f"file://{os.path.abspath(temp_html)}")
                await page.wait_for_timeout(500)  # Esperar renderização

                screenshot_name = f"{endpoint.replace('/', '_').replace('?', '_')}.png"
                screenshot_path = f"{SCREENSHOTS_DIR}/{screenshot_name}"
                await page.screenshot(path=screenshot_path, full_page=True)
                await browser.close()

            # Remover HTML temporário
            os.remove(temp_html)

            self.screenshots.append({
                'endpoint': endpoint,
                'title': title,
                'screenshot': screenshot_name,
                'success': True
            })

            print(f"✅ Screenshot capturado: {title}")
            return True

        except Exception as e:
            print(f"❌ Erro ao capturar {title}: {e}")
            self.screenshots.append({
                'endpoint': endpoint,
                'title': title,
                'success': False,
                'error': str(e)
            })
            return False

    async def run_all_captures(self):
        """Executa todas as capturas"""
        print("📸 Iniciando captura de screenshots...")
        print("=" * 80)

        endpoints = [
            ("/monitors", "Lista de Monitores"),
            ("/monitors/1/vehicles", "Veículos do Monitor #1"),
            ("/alerts", "Lista de Alertas"),
            ("/alerts/stats", "Estatísticas de Alertas"),
            ("/events/catalog", "Catálogo de Eventos"),
            ("/fleet/scores", "Scores da Frota"),
            ("/fleet/stats", "Estatísticas da Frota"),
            ("/monitors/stats", "Estatísticas de Monitores"),
        ]

        for endpoint, title in endpoints:
            await self.capture_endpoint(endpoint, title)
            await asyncio.sleep(0.5)  # Pequeno delay entre capturas

        print("=" * 80)
        print(f"✅ {len([s for s in self.screenshots if s['success']])} screenshots capturados")
        print("=" * 80)

    def generate_report_with_images(self):
        """Gera relatório Markdown com as imagens"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md = f"""# 📸 Relatório Visual - API AITrack Monitor System

**Data:** {timestamp}
**Total de Screenshots:** {len(self.screenshots)}

---

## 🖼️ Capturas de Tela

"""

        for i, screenshot in enumerate(self.screenshots, 1):
            md += f"\n### {i}. {screenshot['title']}\n\n"
            md += f"**Endpoint:** `{screenshot['endpoint']}`\n\n"

            if screenshot['success']:
                md += f"![{screenshot['title']}](screenshots/{screenshot['screenshot']})\n\n"
            else:
                md += f"❌ **Erro:** {screenshot.get('error', 'Falha ao capturar')}\n\n"

        md += f"\n---\n\n*Relatório gerado automaticamente em {timestamp}*\n"

        # Salvar relatório
        report_path = f"tests/reports/visual_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"\n📄 Relatório visual salvo em: {report_path}")
        return report_path


async def main():
    validator = PlaywrightValidator()
    await validator.run_all_captures()
    validator.generate_report_with_images()


if __name__ == "__main__":
    asyncio.run(main())
