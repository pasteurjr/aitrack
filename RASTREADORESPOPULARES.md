# Relatório de Rastreadores GPS Populares e Protocolos de Comunicação

## 1. Introdução

Este relatório detalha as características técnicas e os protocolos de comunicação de rastreadores GPS populares no mercado brasileiro e mundial, com foco nas informações necessárias para a construção de um servidor de ingestão de dados como o do sistema AITrack.

### **Nota Importante sobre WebSockets vs. Sockets TCP/UDP**

É crucial esclarecer que a grande maioria dos rastreadores GPS **não utiliza WebSockets** para comunicação. Eles empregam protocolos de mais baixo nível, enviando dados brutos através de conexões **TCP** ou **UDP** para um endereço IP e uma porta específicos.

- **Socket TCP/UDP:** O rastreador abre uma conexão direta com o IP do seu servidor em uma porta (ex: `200.150.100.50:9000`) e envia uma sequência de bytes (em formato texto/ASCII ou binário). O trabalho do seu servidor é "escutar" nessa porta, aceitar a conexão e "traduzir" essa sequência de bytes.
- **WebSocket:** É um protocolo de comunicação construído sobre o TCP, geralmente iniciado por uma requisição HTTP. É usado primariamente por aplicações web (navegadores) e não por dispositivos IoT/M2M de baixo nível.

Portanto, o servidor de ingestão do AITrack deverá ser um **servidor de sockets TCP/UDP**, não um servidor WebSocket.

---

## 2. Maxtrack

A Maxtrack é uma marca brasileira muito popular, conhecida pela sua robustez e ampla utilização em frotas.

- **Modelos Populares:** MXT-140, MXT-141, MTC-700.
- **Características Técnicas Gerais (MXT-140):**
    - Comunicação GPRS Quad-Band.
    - Antenas internas de GPS e GPRS.
    - Bateria de backup interna.
    - 1 entrada digital, 1 saída a relé.
    - Acelerômetro de 3 eixos.
    - Tensão de alimentação: 6 a 45 VDC.
    - Resistência à água (IP67).

### Protocolo de Comunicação (Maxtrack Padrão)

- **Transporte:** TCP.
- **Formato:** ASCII (Texto).
- **Estrutura da Mensagem de Posição:** A mensagem é uma string de texto com campos separados por ponto e vírgula `;`, começando com `>` e terminando com `<`.

**Exemplo de String de Posição:**
`>REV01;230825;113000;A;-23.55052;-046.63331;015.5;045;1;12.5;1;3<`

**Análise do Protocolo:**
- `>REV01`: Cabeçalho e versão do protocolo.
- `230825`: Data (AAMMDD - 23 de Agosto de 2025).
- `113000`: Hora (HHMMSS - 11:30:00 UTC).
- `A`: Status do GPS (`A` = Válido, `V` = Inválido).
- `-23.55052`: Latitude (em graus decimais).
- `-046.63331`: Longitude (em graus decimais).
- `015.5`: Velocidade (em km/h).
- `045`: Curso/Heading (em graus, 0-359).
- `1`: Status da Ignição (`1` = Ligada, `0` = Desligada).
- `12.5`: Tensão da bateria principal (em Volts).
- `1`: Evento que gerou a transmissão (ex: `1`=posição por tempo, `3`=ignição ligada, etc.).
- `3`: Altitude (neste exemplo, o campo pode variar; a altitude nem sempre está presente ou pode estar em outra posição dependendo da configuração). O protocolo Maxtrack tem muitas variações.

---

## 3. Suntech

Suntech é outra marca extremamente popular, com uma vasta gama de modelos e documentação de protocolo geralmente acessível.

- **Modelos Populares:** ST310U, ST340, ST4310.
- **Características Técnicas Gerais (ST310U):**
    - Comunicação GPRS.
    - Bateria de backup.
    - 1 entrada digital, 1 saída digital.
    - Acelerômetro de 3 eixos.
    - Detecção de Jamming.
    - Tensão de alimentação: 8 a 40 VDC.

### Protocolo de Comunicação (Suntech Padrão)

- **Transporte:** TCP.
- **Formato:** ASCII (Texto).
- **Estrutura da Mensagem de Posição:**

**Exemplo de String de Posição (Live):**
`ST310U;123456789012345;01;20250823;11:30:00;-23.55052;-46.63331;15.5;45.0;1;1;12.5;3.7;100;1;BR;724;31;1234;5678`

**Análise do Protocolo:**
- `ST310U`: Modelo do dispositivo.
- `123456789012345`: ID do dispositivo (IMEI).
- `01`: Tipo de Mensagem (`01` = Posição em tempo real).
- `20250823`: Data (AAAAMMDD).
- `11:30:00`: Hora (HH:MM:SS UTC).
- `-23.55052`: Latitude.
- `-46.63331`: Longitude.
- `15.5`: Velocidade (em km/h).
- `45.0`: Curso/Heading (em graus).
- `1`: Status da Ignição (`1`=Ligada).
- `1`: Status da Entrada Digital 1.
- `12.5`: Tensão da alimentação principal.
- `3.7`: Tensão da bateria de backup.
- `100`: Nível do sinal GPRS (0-100).
- `1`: Número de satélites GPS.
- `BR`: Código do País (MCC).
- `724`: Código da Operadora (MNC).
- `31`: LAC (Location Area Code).
- `1234`: Cell ID.
- `5678`: Odômetro.
- **Altitude:** Geralmente vem em um tipo de mensagem diferente ou como um campo adicional, dependendo da configuração do reporte.

---

## 4. Queclink

Queclink é uma gigante global, com dispositivos conhecidos pela sua confiabilidade e pela documentação detalhada do protocolo.

- **Modelos Populares:** GV55, GL300, GV300.
- **Características Técnicas Gerais (GV55 - versão Mini):**
    - Comunicação GPRS.
    - Antenas internas.
    - Bateria de backup.
    - 1 entrada digital, 1 saída digital.
    - Acelerômetro de 3 eixos.
    - Detecção de Jamming.
    - Tensão de alimentação: 8 a 32 VDC.

### Protocolo de Comunicação (@Track Protocol)

- **Transporte:** TCP ou UDP.
- **Formato:** ASCII (Texto).
- **Estrutura da Mensagem de Posição:** As mensagens geralmente começam com `+RESP:` ou `+BUFF:`.

**Exemplo de String de Posição (Tipo GTRIC):**
`+RESP:GTRIC,123456789012345,1,1,0,7,230825,113000,-23.55052,-46.63331,15.5,45,1,100,12.5,98765,1234,5678,724,31,1,150.0<CR><LF>`

**Análise do Protocolo:**
- `+RESP:GTRIC`: Cabeçalho da resposta para um evento de posição (`RIC`).
- `123456789012345`: IMEI.
- `1`: Report Type.
- `1`: Número da mensagem.
- `0`: Nível da bateria de backup (0-6).
- `7`: Nível do sinal GSM (0-7).
- `230825`: Data (AAMMDD).
- `113000`: Hora (HHMMSS UTC).
- `-23.55052`: Latitude.
- `-46.63331`: Longitude.
- `15.5`: Velocidade (em km/h).
- `45`: Curso/Heading.
- `1`: Status da Ignição.
- `100`: Odômetro.
- `12.5`: Tensão da alimentação externa.
- `98765`: ID do relatório.
- `1234`: Cell ID.
- `5678`: LAC.
- `724`: MNC.
- `31`: MCC.
- `1`: Contagem de satélites.
- `150.0`: Altitude (em metros).
- `<CR><LF>`: Terminadores (Carriage Return, Line Feed).

---

## 5. Continental e Magneti Marelli

Essas duas empresas são gigantes do setor automotivo e atuam primariamente como fornecedoras **Tier 1 (OEM)**, ou seja, fornecem componentes diretamente para as montadoras de veículos.

- **Produtos:** Telematics Control Units (TCU), V2X (Vehicle-to-Everything) modules, In-Vehicle Infotainment (IVI).
- **Características Técnicas:** Seus produtos são muito mais complexos que simples rastreadores GPS. Eles se integram profundamente com a rede interna do veículo (CAN Bus, Ethernet automotiva) e podem coletar centenas de parâmetros diretamente da ECU do motor, do chassi, etc. Suportam tecnologias como 4G/5G, V2X, eCall (chamada de emergência automática) e diagnósticos remotos.

### Protocolo de Comunicação

A documentação detalhada do protocolo de comunicação GPRS/4G para os dispositivos da **Continental** e **Magneti Marelli** é **proprietária e não divulgada publicamente**.

- **Motivo:** O acesso é concedido apenas a parceiros de integração (como as próprias montadoras ou grandes plataformas de serviço) sob estritos acordos de confidencialidade (NDA). A comunicação é complexa, muitas vezes usando formatos binários customizados, criptografia e protocolos específicos da indústria automotiva.
- **Abordagem para Integração:** Para integrar com esses dispositivos, seria necessário um contrato comercial direto com a empresa para obter acesso aos SDKs e à documentação do protocolo, o que está fora do escopo de projetos de desenvolvimento padrão.
