#!/usr/bin/env python3
"""Captura as telas reais usadas pelo roteiro executivo de cinco minutos."""

import json
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


BASE_URL = 'http://127.0.0.1:3000'
OUTPUT = Path(__file__).resolve().parents[1] / 'docs/video-5min/screenshots'


def shot(page: Page, name: str, description: str, manifest: list[dict]) -> None:
    page.wait_for_timeout(900)
    page.screenshot(path=str(OUTPUT / name), full_page=False)
    manifest.append({
        'arquivo': name,
        'descricao': description,
        'capturado_em': datetime.now().astimezone().isoformat(),
    })


def tab(page: Page, label: str) -> None:
    page.get_by_role('button', name=re.compile(label, re.I)).first.click()
    page.wait_for_timeout(1200)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
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
            'status': response.status,
            'url': response.url,
        }) if response.status >= 400 else None)

        page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
        page.get_by_role('status', name='Ambiente: SIMULAÇÃO').wait_for(timeout=20000)
        page.get_by_text('2 exibida(s)', exact=False).wait_for(timeout=20000)
        shot(page, '01_abertura_dashboard.png',
             'Dashboard integrado com Tracker, Dirija Bem e duas cercas operacionais.', manifest)

        page.locator('select').nth(1).select_option('1')
        page.get_by_text(re.compile('Veículo Dirija Bem')).first.wait_for(timeout=20000)
        page.wait_for_timeout(5000)
        shot(page, '02_dirijabem_rota_posicao_inicial.png',
             'Motorista sintético Dirija Bem selecionado, com rota persistida.', manifest)
        page.wait_for_timeout(12000)
        shot(page, '03_dirijabem_rota_posicao_atualizada.png',
             'Mesma viagem Dirija Bem após novo ciclo de atualização.', manifest)

        page.locator('select').nth(1).select_option('')
        page.locator('select').nth(0).select_option('SIM-1008')
        page.wait_for_timeout(3500)
        shot(page, '04_tracker_selecionado.png',
             'Veículo Tracker selecionado e identificado pela origem.', manifest)

        tab(page, 'Timeline')
        page.get_by_text('TIMELINE DE EVENTOS').wait_for(timeout=20000)
        shot(page, '05_timeline_eventos.png',
             'Timeline real com filtros e eventos produzidos pelo simulador.', manifest)
        first_event = page.get_by_role('button', name=re.compile('Excesso de Velocidade|Curva')).first
        if first_event.count():
            first_event.click()
            page.wait_for_timeout(1800)
        shot(page, '06_evento_destacado_mapa.png',
             'Evento selecionado, correlacionado ao veículo e ao mapa.', manifest)

        tab(page, 'Dashboard')
        page.get_by_text('2 exibida(s)', exact=False).wait_for(timeout=20000)
        page.wait_for_timeout(2500)
        shot(page, '07_cercas_operacionais.png',
             'Cerca circular e poligonal com alvos, estados e violações ao vivo.', manifest)

        tab(page, 'Incidentes')
        page.get_by_text('Fila de incidentes').wait_for(timeout=20000)
        page.get_by_label('Tipo de incidente').select_option('geofence_violation')
        page.get_by_text('Saída de cerca eletrônica', exact=True).first.wait_for(timeout=20000)
        shot(page, '08_incidentes_cerca_filtrados.png',
             'Fila filtrada com incidentes persistidos de entrada e saída de cerca.', manifest)
        page.get_by_text('Saída de cerca eletrônica', exact=True).first.click()
        page.get_by_text('Timeline auditável', exact=False).wait_for(timeout=20000)
        shot(page, '09_incidente_cerca_detalhe.png',
             'Detalhe auditável do incidente de cerca e suas evidências.', manifest)

        tab(page, 'Monitores AI')
        page.get_by_text('Monitores AI', exact=False).first.wait_for(timeout=20000)
        shot(page, '10_monitores_operacionais.png',
             'Lista de monitores persistidos, estados, veículos e intervalos.', manifest)

        browser.close()

    (OUTPUT.parent / 'manifesto_capturas.json').write_text(json.dumps({
        'base_url': BASE_URL,
        'viewport': '1920x1080',
        'capturas': manifest,
        'page_errors': page_errors,
        'http_errors': http_errors,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    if page_errors or http_errors:
        raise RuntimeError({'page_errors': page_errors, 'http_errors': http_errors})
    print(f'{len(manifest)} capturas geradas em {OUTPUT}')


if __name__ == '__main__':
    main()
