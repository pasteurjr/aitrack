
# Especificação Técnica v1.0 - Sistema de Rastreamento Veicular AITrack

## 1. Introdução

### 1.1. Visão Geral
O AITrack é um sistema avançado de rastreamento e monitoramento veicular projetado para oferecer segurança aprimorada, eficiência operacional e insights proativos através do uso intensivo de agentes inteligentes. O sistema será capaz de receber, processar e armazenar dados de geolocalização de uma variedade de rastreadores populares (ex: Continental, Maxtrack, etc.) e apresentar essas informações em uma aplicação web intuitiva e poderosa.

O diferencial do AITrack reside em sua camada de inteligência artificial, que não apenas exibe dados, mas os interpreta para prever problemas, detectar anomalias, otimizar operações e aumentar a segurança dos ativos monitorados.

### 1.2. Escopo do Sistema
Esta especificação cobre os seguintes componentes principais:
- **Servidor de Ingestão de Dados:** Um serviço robusto baseado em sockets para receber dados de múltiplos protocolos de rastreadores.
- **Servidor de Aplicação:** Um backend em Python/Flask que serve uma API RESTful para a aplicação web e executa a lógica dos agentes inteligentes.
- **Banco de Dados:** Um banco de dados relacional com capacidades geoespaciais para armazenar dados de posição, veículos, usuários e alertas.
- **Aplicação Web de Monitoramento:** Uma interface de usuário rica para visualização em tempo real, relatórios, configuração e interação com os agentes.
- **Agentes Inteligentes:** Um conjunto de serviços autônomos que analisam dados para fornecer insights e ações automatizadas.

---

## 2. Arquitetura do Sistema

### 2.1. Diagrama de Alto Nível
```
[Rastreadores Veiculares] --(TCP/UDP)--> [Servidor de Ingestão (Python Sockets)]
                                                    |
                                                    v
                [Fila de Mensagens (ex: RabbitMQ)] -> [Servidor de Aplicação (Python/Flask)]
                                                                    |
                                                                    v
                                                    [Banco de Dados (PostgreSQL + PostGIS)]
                                                                    ^
                                                                    |
[Aplicação Web (React/Vue)] <--(API RESTful)--> [Servidor de Aplicação] <--> [Agentes Inteligentes]
```

### 2.2. Componentes

#### 2.2.1. Servidor de Ingestão de Dados
- **Tecnologia:** Python, utilizando a biblioteca `socket` para criar listeners TCP e UDP.
- **Funcionalidade:**
    - Manterá portas abertas para escutar as conexões dos rastreadores.
    - Implementará um design de "Adaptador de Protocolo" (Protocol Adapter), onde cada família de rastreadores (Maxtrack, Continental, etc.) terá seu próprio parser.
    - O servidor identificará o tipo de rastreador (pela porta de conexão ou por um byte de identificação) e passará os dados brutos para o parser correspondente.
    - O parser traduzirá os dados para um formato JSON padronizado (ex: `{ "device_id": "...", "latitude": ..., "longitude": ..., "timestamp": ..., "ignition": ..., "speed": ... }`).
    - As mensagens padronizadas serão publicadas em uma fila de mensagens para processamento assíncrono, garantindo que o servidor de ingestão permaneça leve e responsivo.

#### 2.2.2. Servidor de Aplicação
- **Tecnologia:** Python, com o framework Flask ou FastAPI.
- **Funcionalidade:**
    - Consumirá as mensagens da fila, validará os dados e os persistirá no banco de dados.
    - Fornecerá uma API RESTful segura para a aplicação web, com endpoints para:
        - Autenticação de usuários.
        - CRUD de veículos, usuários e geocercas.
        - Consulta de posições históricas e em tempo real.
        - Geração de relatórios.
        - Gerenciamento de alertas.
    - Orquestrará a execução dos agentes inteligentes, seja por gatilhos (ex: nova posição recebida) ou de forma agendada (ex: análise de rotina diária).

#### 2.2.3. Banco de Dados
- **Tecnologia:** PostgreSQL com a extensão PostGIS.
- **Justificativa:** PostGIS oferece tipos de dados e funções especializadas para consultas geoespaciais, que são essenciais para operações como "encontrar veículos dentro de uma área" ou "verificar se um ponto está dentro de uma geocerca".
- **Schema Principal (Simplificado):**
    - `vehicles`: (id, license_plate, model, tracker_id)
    - `positions`: (id, vehicle_id, timestamp, coordinates (GEOMETRY), speed, ignition_status)
    - `users`: (id, name, email, password_hash)
    - `geofences`: (id, name, area (POLYGON))
    - `alerts`: (id, vehicle_id, timestamp, alert_type, description, position_id)

#### 2.2.4. Aplicação Web de Monitoramento
- **Tecnologia:** Framework moderno de frontend (React, Vue ou Angular) com uma biblioteca de mapas (Leaflet, Mapbox ou OpenLayers).
- **Funcionalidades Padrão:**
    - Visualização de múltiplos veículos em tempo real em um mapa.
    - Playback de rotas históricas.
    - Criação e gerenciamento de geocercas (cercas virtuais).
    - Relatórios (distância percorrida, tempo de ignição ligada, paradas, etc.).
    - Sistema de alertas configuráveis (ex: excesso de velocidade, entrada/saída de geocerca).
    - Dashboard com estatísticas gerais da frota.

---

## 3. Agentes Inteligentes para Segurança e Eficiência

Os agentes inteligentes são o coração do AITrack. Eles operam em segundo plano, analisando o fluxo de dados para fornecer uma camada proativa de gerenciamento.

**1. Agente "Sentinela de Rota"**
- **Objetivo:** Detectar desvios de rota não autorizados que possam indicar roubo ou uso indevido.
- **Funcionamento:** O agente aprende as rotas mais comuns para cada veículo com base no histórico. Se um veículo realizar um desvio significativo de uma rota esperada (especialmente em horários incomuns), o agente gera um alerta de "Desvio Suspeito".
- **Interação:** Exibe um alerta de alta prioridade no dashboard e pode enviar notificações push/SMS para o gestor.

**2. Agente "Vigia Noturno"**
- **Objetivo:** Prevenir roubos de veículos estacionados.
- **Funcionamento:** Aprende os horários e locais onde cada veículo costuma ficar estacionado (ex: garagem de casa à noite, estacionamento da empresa durante o dia). Se a ignição for ligada ou o veículo se mover para fora de uma "zona de segurança" implícita durante esses períodos, um alerta de "Atividade Incomum" é gerado.
- **Interação:** Alerta de criticidade alta, sugerindo uma verificação imediata.

**3. Agente "Detector de Jammer"**
- **Objetivo:** Identificar tentativas de bloqueio de sinal GPS/GPRS.
- **Funcionamento:** Monitora a comunicação dos rastreadores. Uma perda de sinal súbita e prolongada, especialmente em áreas urbanas com boa cobertura ou se outros veículos próximos continuam reportando, é um forte indicativo de uso de jammer. O agente cruza essa informação com a última localização conhecida.
- **Interação:** Gera um alerta de "Possível Bloqueio de Sinal", marcando a última posição válida no mapa com um ícone de alerta.

**4. Agente "Mecânico Preditivo"**
- **Objetivo:** Reduzir custos de manutenção e evitar quebras.
- **Funcionamento:** Analisa dados como horas de motor, quilometragem e (se disponível no rastreador) voltagem da bateria e códigos de falha da ECU. Com base em padrões, ele prevê a necessidade de manutenções (troca de óleo, revisão) e detecta anomalias (ex: bateria com voltagem caindo progressivamente).
- **Interação:** Exibe um "Cartão de Saúde do Veículo" no dashboard, com recomendações de manutenção.

**5. Agente "Perfil de Condução"**
- **Objetivo:** Aumentar a segurança e reduzir custos com combustível e manutenção.
- **Funcionamento:** Analisa eventos como aceleração brusca, frenagem forte, curvas acentuadas e excesso de velocidade para criar um "score" de condução para cada motorista/veículo.
- **Interação:** Apresenta um ranking de motoristas e relatórios detalhados sobre o comportamento de direção, permitindo treinamentos e bonificações.

**6. Agente "Anti-Clone"**
- **Objetivo:** Detectar clonagem de identificação do rastreador.
- **Funcionamento:** Procura por anomalias lógicas, como um mesmo ID de veículo reportando de duas localizações diferentes simultaneamente ou realizando "saltos" geograficamente impossíveis (ex: estar em São Paulo e 1 minuto depois em Belo Horizonte).
- **Interação:** Bloqueia o ID suspeito e gera um alerta crítico para a administração do sistema.

**7. Agente "Geofence Inteligente"**
- **Objetivo:** Simplificar a criação de geocercas.
- **Funcionamento:** Identifica locais de parada recorrentes (ex: centros de distribuição, clientes, postos de gasolina) e sugere automaticamente a criação de geocercas nomeadas para esses locais. "Veículo passou 3 horas neste local. Deseja criar a geocerca 'Cliente X' aqui?".
- **Interação:** Apresenta sugestões no mapa ou em uma lista de tarefas para o gestor.

**8. Agente "Otimizador de Frota"**
- **Objetivo:** Melhorar a eficiência logística.
- **Funcionamento:** Para frotas, o agente pode analisar um conjunto de entregas ou visitas planejadas e, considerando o trânsito em tempo real (via integração com APIs externas) e a localização atual dos veículos, sugerir a alocação mais eficiente de tarefas para cada veículo.
- **Interação:** Mostra uma visão otimizada de rotas e atribuições no mapa.

**9. Agente "Guardião de Carga"**
- **Objetivo:** Aumentar a segurança de cargas valiosas.
- **Funcionamento:** Se o rastreador tiver sensores de porta, o agente monitora aberturas de baú. Uma abertura fora de uma geocerca autorizada (como um centro de distribuição ou cliente) gera um alerta imediato.
- **Interação:** Alerta crítico com a localização exata da ocorrência.

**10. Agente "Analista de Tendências"**
- **Objetivo:** Fornecer insights de negócio a partir dos dados de rastreamento.
- **Funcionamento:** De forma agendada (semanal/mensal), o agente analisa dados agregados para identificar tendências, como: o tempo médio de parada em clientes, os veículos mais e menos eficientes, os horários de maior ociosidade da frota, etc.
- **Interação:** Gera e envia por e-mail um relatório executivo com gráficos e insights chave.

---

## 4. Próximos Passos

1.  **Prova de Conceito (PoC):**
    - Desenvolver o servidor de socket básico para um único tipo de protocolo de rastreador.
    - Configurar o banco de dados com o schema inicial.
    - Criar um script para receber, parsear e salvar as posições.
2.  **Desenvolvimento do Backend:**
    - Implementar a API RESTful com autenticação.
    - Desenvolver os endpoints para as funcionalidades básicas.
3.  **Desenvolvimento do Frontend:**
    - Criar a interface de mapa e a exibição de veículos.
4.  **Implementação dos Agentes:**
    - Começar com os agentes de maior impacto na segurança, como o "Sentinela de Rota" e o "Vigia Noturno".
