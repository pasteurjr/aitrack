#!/usr/bin/env python3
"""Captura o roteiro visual da App 2 com dados reais dos simuladores."""

import json
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


BASE_URL = 'http://127.0.0.1:3000'
OUTPUT_DIR = Path(__file__).resolve().parents[1] / 'docs/video-demo/screenshots'


def capture(page: Page, filename: str, description: str, manifest: list[dict]) -> None:
    page.wait_for_timeout(800)
    path = OUTPUT_DIR / filename
    page.screenshot(path=str(path), full_page=False)
    manifest.append({
        'arquivo': filename,
        'descricao': description,
        'capturado_em': datetime.now().astimezone().isoformat(),
    })


def click_tab(page: Page, label: str) -> None:
    page.get_by_role('button', name=re.compile(re.escape(label))).first.click()
    page.wait_for_timeout(1200)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    page_errors: list[str] = []
    http_errors: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path='/usr/bin/google-chrome-stable',
            args=['--no-sandbox'],
        )
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.on('pageerror', lambda error: page_errors.append(str(error)))
        page.on('response', lambda response: http_errors.append({
            'status': response.status, 'url': response.url,
        }) if response.status >= 400 else None)

        page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
        page.get_by_role('status', name='Ambiente: SIMULAÇÃO').wait_for(timeout=20000)
        page.get_by_text('Fleet Behavioral Dashboard').wait_for(timeout=20000)
        capture(page, '01_dashboard_visao_geral.png',
                'Dashboard, origem Tracker/Dirija Bem, indicadores e mapa.', manifest)

        page.locator('select').nth(0).select_option('SIM-1008')
        page.wait_for_timeout(3500)
        capture(page, '02_tracker_veiculo_rastreado.png',
                'Veículo Tracker selecionado, posição/trilha e contexto do veículo.', manifest)

        page.locator('select').nth(0).select_option('')
        page.locator('select').nth(1).select_option('1')
        page.wait_for_timeout(3500)
        capture(page, '03_dirijabem_motorista_viagem.png',
                'Motorista Dirija Bem selecionado e viagem sintética gravada no banco.', manifest)

        page.get_by_text('FROTA UNIFICADA').scroll_into_view_if_needed()
        capture(page, '04_frota_unificada_origens.png',
                'Lista unificada preservando origem, identidade e modo operacional.', manifest)

        click_tab(page, 'Timeline')
        page.get_by_text('TIMELINE DE EVENTOS').wait_for(timeout=15000)
        capture(page, '05_timeline_eventos_filtros.png',
                'Timeline com filtros por tipo, severidade e período.', manifest)
        event_button = page.get_by_role('button', name=re.compile('Excesso de Velocidade|Curva Brusca')).first
        if event_button.count():
            event_button.click()
            page.wait_for_timeout(1800)
            capture(page, '06_timeline_evento_no_mapa.png',
                    'Seleção de evento correlacionada ao veículo e ao mapa.', manifest)

        click_tab(page, 'Análises')
        page.get_by_text('ANÁLISES COMPORTAMENTAIS').wait_for(timeout=15000)
        capture(page, '07_analises_comportamentais.png',
                'Distribuição de eventos, ranking e correlação score versus eventos.', manifest)

        click_tab(page, 'Monitores AI')
        page.get_by_text('Monitor #1', exact=True).first.wait_for(timeout=15000)
        capture(page, '08_monitores_lista.png',
                'Lista persistida de monitores, estado e intervalos de análise.', manifest)
        page.get_by_text('Monitor #1', exact=True).first.click()
        page.get_by_text('Eventos persistidos — Monitor #1').wait_for(timeout=15000)
        page.get_by_text('Eventos persistidos — Monitor #1').wait_for(timeout=15000)
        page.get_by_text('Consultando eventos persistidos...').wait_for(state='hidden', timeout=60000)
        capture(page, '09_monitor_detalhe_eventos.png',
                'Monitor com veículos atribuídos; indisponibilidade da consulta detalhada observada.', manifest)
        vehicle = page.get_by_text('SIM-1001', exact=True).first
        if vehicle.count():
            vehicle.click()
            page.get_by_text('Consultando eventos persistidos...').wait_for(state='hidden', timeout=60000)
            capture(page, '10_monitor_veiculo_contextualizado.png',
                    'Veículo do monitor selecionado e contextualizado no mapa.', manifest)

        click_tab(page, 'Incidentes')
        page.get_by_text('Fila de incidentes').wait_for(timeout=20000)
        capture(page, '11_incidentes_fila_sla.png',
                'Fila persistida, filtros, severidade, estados e indicadores de SLA.', manifest)
        page.get_by_text('Excesso de velocidade detectado', exact=True).first.click()
        page.get_by_text('Timeline auditável').wait_for(timeout=15000)
        capture(page, '12_incidente_detalhe_auditoria.png',
                'Detalhe do incidente, evidência, risco, SLA e ações auditáveis.', manifest)
        page.get_by_role('button', name='← Voltar à fila').click()
        page.get_by_role('button', name='Registrar falso negativo').click()
        page.get_by_role('heading', name='Falha de detecção').wait_for(timeout=10000)
        capture(page, '13_incidente_falso_negativo.png',
                'Formulário de falso negativo com veículo, motivo, severidade e evidência.', manifest)
        page.get_by_role('button', name='Cancelar').click()

        click_tab(page, 'Eventos')
        page.get_by_text('Catálogo operacional de eventos').wait_for(timeout=20000)
        capture(page, '14_catalogo_eventos_reais.png',
                'Catálogo real de detectores e contagens produzidas pelos simuladores.', manifest)
        page.get_by_role('button', name=re.compile('Excesso de Velocidade')).first.click()
        page.get_by_text('Detalhes do tipo de evento').wait_for(timeout=10000)
        capture(page, '15_evento_tipo_detalhe.png',
                'Detalhe de um tipo suportado, severidade e ocorrências do dia.', manifest)

        click_tab(page, 'Dashboard')
        page.get_by_role('button', name=re.compile('Criar cerca')).click()
        page.get_by_text('Cerca eletrônica').wait_for(timeout=10000)
        capture(page, '16_cerca_criacao_circular.png',
                'Protótipo visual preliminar da futura cerca circular; fluxo não validado.', manifest)
        page.get_by_role('button', name='⬡ Polígono').click()
        capture(page, '17_cerca_criacao_poligonal.png',
                'Protótipo visual preliminar da futura cerca poligonal; fluxo não validado.', manifest)

        browser.close()

    (OUTPUT_DIR.parent / 'manifesto_capturas.json').write_text(
        json.dumps({
            'base_url': BASE_URL,
            'viewport': '1920x1080',
            'capturas': manifest,
            'page_errors': page_errors,
            'http_errors': http_errors,
        }, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    if page_errors:
        raise RuntimeError(f'Erros JavaScript durante captura: {page_errors}')
    print(f'{len(manifest)} capturas geradas em {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
