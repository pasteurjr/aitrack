# Validação — UI-4.4: aba Sensores do veículo

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 15 de 74  
**Checkpoint anterior:** `00d1df9`

## Resultado esperado

O detalhe do veículo deve apresentar uma aba acessível com sensores efetivamente
suportados/configurados, consultados da API e do banco, sem catálogo local ou dado
mockado.

## Resultado obtido

- O contexto do veículo ganhou abas acessíveis `Mapa e rota` e `Sensores` sem perder
  a seleção unificada Tracker/Dirija Bem.
- A nova API `vehicle-sensors.v1` resolve o veículo operacional e retorna somente
  instâncias que realmente atravessaram a ingestão normalizada.
- Cada cartão identifica capacidade, origem, protocolo, unidade, ciclo ativo/inativo
  e última observação; os rótulos deixam explícitos `SUPORTE CONFIRMADO` e `OBSERVADO`.
- Carregamento, vazio e erro reutilizam `AsyncDataState`; erro não apresenta fallback
  inventado e permite nova tentativa.
- Veículo apenas Dirija Bem sem sensor físico permanece vazio com explicação clara:
  evento comportamental não é convertido em sensor.
- Backend e simulador Tracker foram reiniciados de forma controlada para carregar o
  novo pipeline; o simulador continua enviando dez veículos pela porta 9000.

## Evidências

- Banco real após execução do simulador: **55 sensores**, **10 veículos**, **2
  protocolos**; 25 instâncias Suntech e 30 Queclink. As leituras continuam crescendo
  pelo pipeline real/sintético, não por fixture de interface.
- API real: SIM-1000/veículo operacional 1 retorna 5 sensores Suntech; SIM-1001/2
  retorna 6 Queclink, incluindo altitude comprovada.
- Navegador headless real em 1440×900: seleção de SIM-1000, abertura da aba e
  conferência visual dos cinco cartões, origem, protocolo, unidades e badges.
- Backend: **262 aprovados e 12 integrações opt-in puladas**.
- Frontend: **76 aprovados** em 16 suítes; TypeScript e build de produção aprovados.
- Testes cobrem dados reais do contrato, vazio Dirija Bem, falha/retry e navegação
  Mapa ↔ Sensores preservando a identidade selecionada.

## Limitações e decisões

- A etapa mostra instalação/observação e suporte; valor atual, qualidade/saúde e
  defasagem pertencem à UI-4.5.
- Os parsers geram horário UTC sem offset e o banco usa `DATETIME`; o navegador pode
  exibi-lo sem conversão inequívoca. A normalização de fuso será tratada com a
  apresentação da leitura na próxima etapa, sem alterar o histórico silenciosamente.
- O frontend em execução usa servidor de desenvolvimento e o backend Flask também é
  de desenvolvimento; isso serve à homologação local, não à publicação produtiva.
- O selo global apareceu `NÃO CONFIRMADO` porque a proveniência runtime ainda não
  confirmou ambos os canais como produção, comportamento seguro esperado.

## Conclusão

**Aprovada.** A aba trabalha com telemetria gerada pelos simuladores e persistida no
banco operacional, diferencia ausência de sensor e não transforma dados Dirija Bem
em hardware fictício.
