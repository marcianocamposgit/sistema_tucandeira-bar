# Roteiro para a versão 2.0 (web) do Tucandeira Rock Bar

Cada etapa tem um prompt pronto para colar no Claude Code. Faça uma de cada vez, teste e só então siga para a próxima. Os requisitos completos, a stack e as regras de arquitetura estão no CLAUDE.md.

**Ordem das etapas (dependências):** estrutura + banco + backup → models e services → login/usuários → caixa → mesas/comandas → pagamento → produtos/estoque → relatórios → rede/tablet → entrega.

- O banco e o backup vêm primeiro, porque a partir daí já existem dados que não podem se perder.
- Os services são escritos e testados antes das telas; as rotas só chamam services.
- Usuários vêm antes de tudo que grava operação, porque toda operação registra quem fez.
- O caixa vem antes das comandas, porque só se vende com caixa aberto.
- A tela de produtos vem depois do pagamento porque o cardápio inicial já é carregado no banco na Etapa 1 — dá para vender antes de ter o gerenciador de produtos.

---

## Etapa 0 — Preparação e segurança ✅ concluída

Repositório git, `.gitignore`, `requirements.txt` e commit com o código original.

## Etapa 0.1 — Mudança de plataforma para web ✅ concluída

Versão Tkinter preservada na tag `v1.0-tkinter` e movida para `legado_tkinter/`. Documentação (CLAUDE.md, ROTEIRO.md, README.md) reescrita para a versão web. A antiga etapa de correção de bugs do Tkinter foi descartada.

---

## Etapa 1 — Estrutura Flask, configuração, banco e backup

> Leia o CLAUDE.md. Crie a estrutura de pastas da arquitetura (app.py, servidor.py, config.py, database.py, models/, services/, routes/, templates/, static/css, static/js, tests/). Atualize o requirements.txt (Flask, waitress, Pillow, pytest) e o .gitignore (`data/*.db`, `data/*.db-wal`, `data/*.db-shm`, `data/backups/`, `data/secret_key`). No config.py: NUM_MESAS (8), PORTA (5000), HOST ("0.0.0.0"), TAXA_SERVICO (10%), PRAZO_REMOCAO_ITEM_MINUTOS (2), TEMPO_SESSAO_MINUTOS (15), INTERVALO_ATUALIZACAO_MESAS (5 s), BACKUPS_MANTIDOS (7) e caminhos com pathlib, já separando os arquivos do programa da `PASTA_DADOS` (banco, backups, secret_key, logs; `data/` no desenvolvimento, `C:\TucandeiraBar\dados\` no executável, variável de ambiente `TUCANDEIRA_DADOS`), como descrito no CLAUDE.md — isso prepara o empacotamento da Etapa 10. Crie `formatar_moeda()` num único lugar (valores em centavos) e registre-a como filtro Jinja2 `moeda`. No database.py: conexão SQLite com WAL, foreign_keys, busy_timeout, uma conexão por requisição (no `g` do Flask, mas a função de conexão em si não depende do Flask) e um helper de transação (`BEGIN IMMEDIATE`/commit/rollback). Crie as tabelas para todos os requisitos da versão 2.0: usuários, categorias, produtos (com estoque mínimo e ativo), entradas de estoque, caixas, movimentos de caixa (sangria/suprimento), comandas (mesa ou nome do cliente, nº de pessoas, status aberta/conta pedida/paga, mesas juntas, taxa ativa), itens da comanda (com observação e data/hora do lançamento), itens cancelados (motivo, gerente), vendas, itens da venda, pagamentos (vários por venda), descontos e configurações (valor do couvert, dia de show). Todas as tabelas de operação guardam o usuário e a data/hora. Controle de versão do esquema com `PRAGMA user_version`, para migrar sem perder dados. Na primeira execução, carregue as 4 categorias e os 6 produtos de `legado_tkinter/main.py` (copiando os valores, sem importar o arquivo). Crie services/backup.py: ao iniciar o servidor, cópia do banco em data/backups usando a API de backup do sqlite3 (segura com WAL), mantendo as 7 últimas. Baixe a fonte Anton (licença OFL) para static/fonts/ (`Anton-Regular.woff2` + `.ttf` + `OFL.txt`) e declare-a com `@font-face` no CSS, com Impact só como alternativa. Crie uma rota inicial que mostre a logo e o texto "Tucandeira Rock Bar" em Anton com o visual do bar (base.html + CSS), para confirmar que o Flask está no ar. **Mostre o esquema das tabelas antes de implementar.**

**Teste:** `python app.py` e abrir `http://localhost:5000` mostra a página inicial com a logo, o fundo verde e o título em Anton (conferir na aba Rede das ferramentas do navegador que a fonte vem de `/static/fonts/`); `data/tucandeira.db` é criado com os 6 produtos e as 4 categorias e com `journal_mode=wal`; iniciar de novo não duplica nada e cria um backup em `data/backups`; com mais de 7 inicializações, só ficam 7 backups; `pytest` passando (testes do banco e do backup com pasta temporária).

---

## Etapa 2 — Models e services com testes

> Crie os models como dataclasses e os services de regra de negócio, **sem nenhum import de Flask**, cada um com testes pytest usando banco temporário. Exceções próprias num módulo comum (ex.: `services/erros.py`: `CaixaFechadoError`, `PermissaoNegadaError`, `PinInvalidoError`, `ComandaFechadaError`, `PrazoRemocaoExpiradoError`...).
> - **services/usuarios.py:** cadastrar (nome, PIN de 4 dígitos, perfil Operador ou Gerente), editar, desativar, autenticar por PIN, `autorizar_gerente(pin)` que devolve o gerente ou lança `PermissaoNegadaError`. PIN com hash + salt (`hashlib.pbkdf2_hmac`). Não permitir PIN repetido nem desativar o último gerente.
> - **services/produtos.py:** listar cardápio por categoria (só ativos), cadastrar, editar, desativar; validar nome duplicado e preço negativo; categorias (criar, renomear, desativar); estoque mínimo; entrada de mercadoria (quantidade, custo opcional, usuário, data); baixa de estoque que pode ficar negativa, informando se ficou abaixo do mínimo ou negativa.
> - **services/caixa.py:** abrir caixa com fundo de troco; sangria (exige gerente) e suprimento, ambos com motivo; caixa aberto atual; conferência de fechamento por forma de pagamento (esperado x contado x diferença; dinheiro esperado = fundo + vendas em dinheiro + suprimentos − sangrias); fechar (exige gerente). Só um caixa aberto por vez.
> - **services/comandas.py:** abrir comanda de mesa (nº de pessoas) ou de balcão (nome do cliente, várias ao mesmo tempo); adicionar item com observação (avisa sem estoque, mas permite); remover item sem PIN até `PRAZO_REMOCAO_ITEM_MINUTOS` após o lançamento; depois disso, só cancelar com motivo e PIN de gerente, registrado; alterar nº de pessoas; marcar/desmarcar "conta pedida"; transferir para mesa livre; juntar mesas (as comandas viram uma só e as mesas ficam vinculadas até o pagamento); listar comandas abertas e estado de todas as mesas (livre, ocupada, conta pedida, pessoas, total parcial); subtotal. Tudo exige caixa aberto. Cada operação que altera várias tabelas roda numa transação e confere se a comanda ainda está aberta.
> Inclua um teste de concorrência: duas conexões lançando itens na mesma comanda ao mesmo tempo (threads) sem perder nenhum item.

**Teste:** `pytest` passando, cobrindo: PIN repetido e último gerente; produto duplicado e preço negativo; conferência do caixa com pagamentos de teste; transferência e junção de mesas; remoção dentro e fora do prazo de 2 minutos (simulando o relógio); cancelamento com e sem PIN de gerente; venda com caixa fechado lança `CaixaFechadoError`; o teste de concorrência.

---

## Etapa 3 — Login por PIN e usuários

> Crie routes/auth.py e routes/usuarios.py e as telas. Primeira execução: se não houver usuários, tela para criar o gerente inicial. Tela de login com teclado numérico grande na tela (botões ≥ 48 px, sem depender de teclado físico) e os 4 dígitos mascarados. Sessão Flask com `SECRET_KEY` gerada na primeira execução e salva em `data/secret_key`; a sessão expira após `TEMPO_SESSAO_MINUTOS` sem uso e volta ao login. Bloqueio temporário após 5 PINs errados seguidos. Decorators `@login_obrigatorio` e um componente reutilizável "PIN do gerente" (modal com teclado numérico em JS simples) que envia o PIN junto com a ação protegida — a autorização vale só para aquela ação. Proteção CSRF nos formulários. Cabeçalho do base.html com a logo, o nome do usuário logado e o botão "Trocar usuário". Tela de usuários (listar, cadastrar, editar, desativar), acessível só com PIN de gerente. Layout responsivo em retrato e paisagem. Escreva testes das rotas com o test client do Flask.

**Teste:** `pytest` passando; criar o gerente inicial, cadastrar um operador, entrar com cada um; o operador não abre a tela de usuários sem o PIN do gerente; deixar o navegador parado além do tempo de sessão e confirmar que volta ao login; testar no navegador em modo de dispositivo (tablet 10", retrato e paisagem).

---

## Etapa 4 — Controle de caixa

> Crie routes/caixa.py e as telas usando services/caixa.py: abrir caixa (fundo de troco com teclado numérico na tela), sangria e suprimento com motivo (sangria pede PIN do gerente), e fechamento com a conferência por forma de pagamento (esperado x contado x diferença, destacando diferenças), pedindo o PIN do gerente. Mostrar no cabeçalho, em todas as telas, se o caixa está aberto ou fechado. Esta tela precisa funcionar bem tanto no tablet (toque) quanto no navegador do computador servidor (mouse e teclado físico, campos aceitando digitação normal). Com o caixa fechado, as telas de venda mostram um aviso e o botão para abrir o caixa.

**Teste:** abrir o caixa com R$ 100,00, fazer uma sangria e um suprimento, fechar e conferir os valores esperados; repetir a operação pelo navegador do computador servidor com mouse e teclado; tentar abrir uma comanda com o caixa fechado e ver o aviso.

---

## Etapa 5 — Tela de mesas e comandas

> Crie routes/mesas.py e as telas usando services/comandas.py. **Tela de mesas:** grade com `NUM_MESAS` mesas em cores diferentes para livre, ocupada e conta pedida, mostrando nº de pessoas e total parcial, e um botão Balcão / Para Viagem; atualiza sozinha a cada `INTERVALO_ATUALIZACAO_MESAS` segundos por uma rota JSON (`fetch` em JS simples), sem recarregar a página inteira. **Tela da comanda:** cardápio por categorias (abas grandes) e comanda com a lista de itens (nome, qtd, observação, subtotal); tocar no produto lança 1 unidade; botões + e − grandes por item; observação por item com atalhos ("sem gelo", "bem passado"...) além do teclado virtual; − remove sem PIN dentro do prazo de 2 minutos e, depois disso, abre o cancelamento com motivo e PIN do gerente; botões "Conta pedida", "Transferir", "Juntar mesas" e "Nº de pessoas"; total em R$ e botão "Fechar Conta" sempre visíveis (em retrato e em paisagem). Cada toque grava no banco na hora; a comanda também se atualiza sozinha para mostrar itens lançados por outro tablet. Botões ficam desativados enquanto a requisição está em andamento, para evitar lançamento duplo. **Balcão:** lista das comandas abertas pelo nome do cliente e botão para criar uma nova.

**Teste:** abrir duas abas (ou dois aparelhos) lado a lado: lançar itens na Mesa 2 numa delas e ver a mesa ficar ocupada e os itens aparecerem na outra em poucos segundos; fechar o navegador, reabrir e conferir a comanda; reiniciar o servidor e conferir de novo; remover um item antes de 2 minutos e tentar depois (deve pedir motivo e PIN); transferir a Mesa 2 para a Mesa 5; juntar as Mesas 3 e 4; abrir duas comandas de balcão com nomes diferentes; usar em retrato e em paisagem.

---

## Etapa 6 — Pagamento

> Crie services/pagamentos.py (com testes pytest) e routes/pagamentos.py com a tela de pagamento. Cálculo da conta: subtotal + taxa de serviço de 10% (ativada por padrão nas mesas, desativada no balcão; removê-la exige PIN do gerente) + couvert artístico por pessoa (quando for dia de show; valor e ativação nas configurações, alterados pelo gerente) − desconto em R$ ou % (com motivo e PIN do gerente). Mostrar os itens, cada parcela da conta e o valor dividido igualmente por pessoa. Permitir dividir entre Dinheiro, Cartão e PIX, mostrando quanto falta; em dinheiro, calcular o troco a partir do valor recebido (teclado numérico na tela e botões de cédulas R$ 10/20/50/100). Só concluir quando o total estiver pago. Ao confirmar, numa única transação: registrar a venda com itens, pagamentos, taxa, couvert, desconto e usuário; baixar o estoque; fechar a comanda; liberar as mesas. Avisar estoque baixo/negativo depois. Proteger contra confirmação dupla (dois tablets ou toque duplo pagando a mesma comanda: só um pagamento vale). A tela de pagamento também deve funcionar no computador servidor (tela de caixa) com mouse e teclado.

**Teste:** `pytest` passando, incluindo dois pagamentos simultâneos da mesma comanda (só um é aceito); pagar uma mesa de 3 pessoas com taxa, couvert e desconto, parte em PIX e parte em dinheiro com troco; conferir o estoque baixado, a mesa livre em todos os tablets e os valores no fechamento do caixa.

---

## Etapa 7 — Produtos e estoque

> Crie routes/produtos.py e as telas usando services/produtos.py (que já existe da Etapa 2). Lista de produtos com nome, categoria, preço, estoque e mínimo, filtro por categoria e destaque para estoque baixo ou negativo; botões para novo, editar, desativar e entrada de mercadoria; gerenciar categorias (criar, renomear, desativar). Cadastro e edição só para gerente (PIN na hora). Formulários adequados para toque (campos grandes, teclado numérico para preço e quantidade) e também usáveis no computador servidor. Alerta de estoque abaixo do mínimo visível na tela de mesas para o gerente.

**Teste:** cadastrar, editar e desativar um produto (o desativado some do cardápio da comanda em todos os tablets); criar uma categoria nova e ver a aba aparecer na comanda; dar entrada de 10 unidades e conferir o estoque; tentar cadastrar nome duplicado ou preço negativo e ver a mensagem de erro.

---

## Etapa 8 — Relatórios

> Crie services/relatorios.py (com testes pytest) e routes/relatorios.py com as telas (acesso de gerente). Relatórios por período (dia, semana, mês e intervalo personalizado com seletor de data do navegador): total vendido, número de vendas, total por forma de pagamento, taxa de serviço e couvert arrecadados, produtos mais vendidos, cancelamentos e descontos (com responsável e motivo), produtos com estoque negativo ou abaixo do mínimo (destacados) e histórico de fechamentos de caixa com as diferenças. Botão para baixar cada relatório em CSV (separador `;` e UTF-8 com BOM para abrir certo no Excel). Tabelas legíveis no tablet (rolagem vertical, sem rolagem horizontal da página) e no computador servidor.

**Teste:** `pytest` passando; conferir os números do relatório contra as vendas feitas nos testes das etapas anteriores; baixar um CSV e abri-lo no Excel com acentos corretos.

---

## Etapa 9 — Acesso pela rede, PWA e teste em tablet real

> Configure o uso real na rede do bar. servidor.py com waitress (`host` e `porta` do config.py, número de threads adequado). Escreva no README como deixar o IP do computador servidor fixo (no Windows ou por reserva DHCP no roteador) e crie um script `scripts/liberar_firewall.ps1` que cria a regra de entrada no Firewall do Windows só para a porta do sistema e só no perfil de rede **Privada** (rodar como administrador; perguntar antes de executar). Mostre no console, ao iniciar, os endereços para acessar (`http://<IP>:<porta>`). Crie o PWA: script com Pillow que gera os ícones 192 e 512 (e apple-touch-icon) a partir de assets/logo.png em static/icones/, `manifest.webmanifest` (nome, cores do bar, `display: fullscreen`, orientação livre) e service worker mínimo, servido na raiz. O service worker só é registrado se `window.isSecureContext` for verdadeiro; sem ele, o sistema funciona normalmente numa aba comum do navegador. Revise todas as telas no tablet antigo e nos celulares: tamanho de toque, retrato e paisagem, comanda em abas no celular, teclado virtual não escondendo o campo em uso, nada dependente de mouse, nenhum recurso de CSS/JS que o Chrome do tablet antigo não suporte.
>
> **Contexto seguro (HTTPS):** service worker e "Instalar app" exigem HTTPS ou `localhost`. Acessando por `http://192.168.x.x`, o tablet pode não oferecer "Instalar app" nem abrir em tela cheia. Documente no README, com passo a passo, as duas soluções:
> 1. **Primeira opção — Chrome do tablet (Android):** abrir `chrome://flags`, procurar "Insecure origins treated as secure", habilitar e informar o endereço do servidor (ex.: `http://192.168.0.10:5000`), tocar em "Relaunch". Depois disso, "Instalar app" passa a aparecer. Precisa ser feito em cada tablet e refeito se o IP ou a porta do servidor mudarem (mais um motivo para o IP fixo).
> 2. **Segunda opção — navegador de quiosque:** instalar um navegador de quiosque em tela cheia (ex.: Fully Kiosk Browser, no Android) apontando para o endereço do servidor, como página inicial, sem barra de endereço. Serve também para iPad ou quando o Chrome não aceitar a flag.

**Teste:** iniciar `python servidor.py` no computador do bar; acessar pelo tablet antigo e por pelo menos um celular de garçom via Wi-Fi em `http://<IP>:<porta>` numa aba comum, **sem** PWA, e confirmar que tudo funciona em cada um (login, lançar item, atualização das mesas, comanda em abas no celular); depois aplicar a 1ª opção (flag do Chrome) no tablet e num celular, instalar o app e abrir em tela cheia com o ícone da logo; se a flag não existir no Chrome do tablet antigo, testar a 2ª opção (navegador de quiosque) nele; com o tablet, dois celulares e o computador servidor ao mesmo tempo, fazer um atendimento completo (abrir mesa, lançar pelo tablet e pelos celulares na mesma comanda, pedir conta, pagar no caixa); bloquear a tela de um celular e confirmar que a atualização automática pausa e volta ao desbloquear; confirmar que um aparelho fora da rede local não acessa.

---

## Etapa 10 — Backup automático, executável, início com o Windows e entrega

> Complete o backup: além do backup ao iniciar o servidor (Etapa 1), um backup diário enquanto o servidor estiver rodando, mantendo os 7 últimos, e um botão "Fazer backup agora" para o gerente com a data do último backup na tela. Gere o pacote de instalação com PyInstaller: `TucandeiraBar.exe` do servidor (a partir de `servidor.py`, com templates, static e assets embutidos, ícone da logo), que roda sem Python instalado; um arquivo `.spec` versionado e um script `scripts/gerar_exe.ps1` para gerar de novo a cada versão. Banco, backups, secret_key e logs ficam na pasta de dados separada (`C:\TucandeiraBar\dados\`), nunca ao lado do executável: atualizar é só trocar `C:\TucandeiraBar\programa\TucandeiraBar.exe`; ao iniciar uma versão nova, o sistema faz backup e migra o banco sozinho. Ao iniciar, o servidor mostra numa janela de console bem visível (título "Tucandeira Rock Bar — Servidor") o endereço completo para digitar nos tablets e celulares (ex.: `http://192.168.0.10:5000`), além de `http://localhost:5000` para o caixa, e o aviso para não fechar a janela. Configure o servidor para iniciar junto com o Windows (tarefa no Agendador de Tarefas ao fazer logon, rodando o `TucandeiraBar.exe` e reiniciando em caso de falha), com um script `scripts/instalar_inicializacao.ps1` e o comando para desfazer (perguntar antes de executar). Log do servidor na pasta de dados (`logs/`) com rotação. Revise o projeto inteiro: tratamento de erros com mensagens amigáveis (páginas 404/500 no visual do bar), nenhuma rota acessando o banco direto, nenhum service importando Flask, nada importando `legado_tkinter/`. Mostrar a versão 2.0 numa tela "Sobre". Atualize o README.md final com o passo a passo de **instalação** no computador do bar (copiar o executável, liberar o firewall, IP fixo, iniciar com o Windows) e de **atualização** (fechar o servidor, trocar o `.exe`, abrir de novo, conferir), além de configuração da rede, uso no tablet e no celular, backup e restauração de um backup.

**Teste:** num computador **sem Python instalado**, instalar seguindo o README e rodar o `TucandeiraBar.exe`; conferir que o banco, os backups e a secret_key foram criados em `C:\TucandeiraBar\dados\` e nada foi gravado ao lado do executável; conferir que a janela mostra o endereço `http://<IP>:<porta>` e acessá-lo pelo tablet e por um celular; reiniciar o computador e, sem abrir nada manualmente, acessar pelo tablet; simular uma atualização trocando o `.exe` por uma versão nova seguindo o README e conferir que os dados continuam lá; conferir o backup do dia na pasta de backups; restaurar um backup numa cópia seguindo o README; atendimento completo: login, abrir o caixa, vender em duas mesas e no balcão, fechar o caixa e ver o relatório.

---

## Versão 2.1 (futuro — não fazer agora)

Impressão térmica de comanda e cupom não fiscal, NFC-e via serviço terceirizado, mais de um servidor ou filiais com dados sincronizados e cardápio digital por QR Code. Ver CLAUDE.md.
