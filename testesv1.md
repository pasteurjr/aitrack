# Plano de Testes v1: Validando o Sistema AITrack

## Introdução

Este documento é um tutorial passo a passo para testar todas as funcionalidades do sistema AITrack que desenvolvemos até agora. O objetivo é validar o fluxo completo: desde a simulação dos dados do rastreador, passando pelo recebimento e processamento no backend, até a visualização em tempo real no frontend.

---

## Pré-requisitos

Para realizar o teste, você precisará de:

1.  **Três (3) janelas de terminal** abertas.
2.  O ambiente **Conda `aitrack`** pronto para ser ativado.
3.  Todos os terminais devem começar no diretório raiz do projeto: `/home/pasteurjr/progreact/aitrack`.

---

## Passo a Passo do Teste

Siga as instruções para cada terminal na ordem apresentada.

### Passo 1: Iniciar o Backend Unificado (Terminal 1)

Neste passo, vamos iniciar nosso servidor principal, que é responsável por receber os dados dos rastreadores (na porta 9000) e por servir a API para o frontend (na porta 5000).

**No Terminal 1, execute os seguintes comandos:**

```bash
# Ative o ambiente Conda
conda activate aitrack

# Inicie o servidor unificado
python run.py
```

**O que esperar:** Você verá mensagens indicando que ambos os servidores foram iniciados. O terminal ficará ativo, mostrando logs à medida que os eventos acontecem.

```
Iniciando todos os serviços AITrack...
Iniciando o Servidor de Socket AITrack...
Iniciando o Servidor da API Flask em http://0.0.0.0:5000...
Servidor escutando em 0.0.0.0:9000
```

### Passo 2: Iniciar o Frontend (Terminal 2)

Agora, vamos iniciar a aplicação de monitoramento em React. Ela irá compilar o código e abrir uma página no seu navegador.

**No Terminal 2, execute os seguintes comandos:**

```bash
# Navegue até a pasta do frontend
cd /home/pasteurjr/progreact/aitrack/frontend

# Inicie o servidor de desenvolvimento do React
npm start
```

**O que esperar:** Após a compilação (`Compiled successfully!`), uma nova aba deve abrir automaticamente no seu navegador, apontando para `http://localhost:3000`. Você verá um mapa de tela cheia, inicialmente centralizado em São Paulo.

### Passo 3: Iniciar o Simulador de Veículos (Terminal 3)

Com os servidores e o frontend no ar, o último passo é gerar dados de teste. O simulador atuará como 10 veículos enviando suas posições para o nosso backend.

**No Terminal 3, execute os seguintes comandos:**

```bash
# Ative o ambiente Conda
conda activate aitrack

# Inicie o simulador
python simulator.py
```

**O que esperar:** Você verá a mensagem `10 veículos simulados iniciados...` seguida por logs de `Enviado pacote...` a cada 10 segundos.

### Passo 4: Validar o Funcionamento (No Navegador)

Volte para a janela do seu navegador que foi aberta no Passo 2 (`http://localhost:3000`).

**Observe o mapa. Dentro de 10 a 15 segundos, você deverá ver:**

1.  **Ícones de Carros Aparecendo:** Vários ícones de carros pretos devem surgir no mapa, na região de São Paulo.
2.  **Popups com Informações:** Ao clicar em um dos ícones, um popup deve aparecer, mostrando a **Placa**, a **Velocidade** e a **Data/Hora** da última atualização daquele veículo.
3.  **Atualização em Tempo Real:** As posições dos carros no mapa devem se mover sutilmente a cada 10 segundos, à medida que o frontend busca e recebe os novos dados da API.
4.  **Logs nos Terminais:** Nos terminais 1 e 3, você continuará vendo logs que mostram o servidor recebendo os dados e o simulador os enviando, confirmando a comunicação.

---

## Como Encerrar o Teste

Quando terminar de validar, basta ir em cada uma das três janelas de terminal e pressionar `Ctrl + C` para encerrar os processos.

## Conclusão

Se você conseguiu observar os carros aparecendo e se movendo no mapa, **o teste foi um sucesso!** Isso valida que todos os componentes do sistema AITrack (Coleta, Armazenamento, API e Visualização) estão integrados e funcionando corretamente.
