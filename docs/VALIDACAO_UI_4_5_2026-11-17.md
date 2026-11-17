# Validação — UI-4.5: valor, saúde, origem e última leitura

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 16 de 74  
**Checkpoint anterior:** `8e9853b`

## Resultado esperado

Permitir que o operador distinga leitura atual, desatualizada, inválida ou
indisponível, veja valor/unidade/qualidade e reconstrua origem e horários sem
normalização silenciosa do relógio do equipamento.

## Resultado obtido

- A API agrega a última leitura imutável de cada sensor e retorna valor tipado,
  unidade, qualidade, idade de gravação, fonte, horário observado, recebido e
  gravado, além do desvio entre os relógios.
- Saúde possui quatro estados explícitos: `current`, `stale`, `invalid` e
  `unavailable`. Qualidade inválida prevalece; sem leitura é indisponível; a idade
  confiável do registro no servidor determina atual/desatualizado.
- O limite de **120 segundos** é uma classificação visual de frescor, não um alerta
  patrimonial nem uma política de offline.
- A interface mostra valor formatado (booleano, número/unidade ou coordenadas),
  badge de saúde, qualidade, recebimento local e horário bruto da fonte com o aviso
  `fuso não informado`.
- Migration 026 removeu a suposição incorreta de que `received_at` sempre é maior
  que `observed_at`. Os dois valores passam a ser preservados.
- Horários do servidor são serializados com offset `-03:00`; horário do equipamento
  permanece sem offset até o protocolo comprová-lo.

## Evidências

- Migration `026_allow_sensor_clock_skew.sql` aplicada e dry-run posterior:
  **0 migrations pendentes**.
- API real para SIM-1000 retornou cinco leituras `current`, qualidade `valid`, idade
  de 1 segundo, recebimento `2026-11-17T16:21:12...-03:00`, observação
  `2026-11-17T19:21:12` e desvio preservado de 10.799 segundos.
- Navegador real 1440×900 mostrou tensão em volts, direção, ignição booleana,
  coordenadas e velocidade, todos com origem Tracker/Suntech, qualidade e horários.
- Backend: **264 aprovados e 12 integrações opt-in puladas**.
- Frontend: **76 aprovados** em 16 suítes; TypeScript e build aprovados.
- Testes unitários cobrem os quatro estados de saúde, valor JSON tipado, fuso do
  servidor, fuso desconhecido da fonte e preservação do desvio de relógio.

## Limitações e decisões

- O limite de 120 s não gera incidente. Offline contextual, manutenção, ignição e
  indisponibilidade da integração serão tratados na UI-4.9 para evitar falso positivo.
- A saúde desta etapa mede frescor/qualidade da leitura; não mede bateria física nem
  integridade elétrica do sensor.
- Leituras antigas gravadas antes da migration podem conter `received_at` igual ao
  horário observado por causa da regra anterior. As novas leituras corrigem o topo
  da timeline sem reescrever o histórico.
- O frontend não converte o horário de fonte sem conhecer o fuso. Essa incerteza é
  apresentada ao operador em vez de ser escondida.

## Conclusão

**Aprovada.** O operador agora vê estado e valor reais com proveniência e incerteza
temporal explícitas, enquanto a classificação de frescor permanece separada da
detecção operacional de offline.
