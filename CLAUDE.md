# Tucandeira Rock Bar — Sistema de Gestão

Sistema web de gestão para bar, em Python + Flask, usado pelo navegador de tablets e celulares na rede local do bar. Um computador do bar é o servidor; o tablet, os celulares dos garçons e o próprio computador do caixa acessam pelo Wi-Fi/rede local. Autor: Marciano Campos.
Todo o código, comentários, nomes de variáveis, mensagens ao usuário e textos das telas devem ser em **português do Brasil**.

## Aparelhos que usam o sistema

**Uso inicial:** um tablet (garçom) e o PC servidor (caixa). Celulares talvez no futuro.

- **Tablet Android antigo, reaproveitado (garçom)** — Android: a confirmar, Chrome: a confirmar. É o aparelho mais limitado e define o mínimo de compatibilidade de CSS e JavaScript.
- **Computador servidor (caixa)** — Windows, navegador atual, com mouse e teclado. É também o **plano B**: se o tablet não conectar, o bar inteiro é operado pelo PC em `http://localhost:5000`, sem depender de Wi-Fi nem de internet.
- **Celulares Android dos garçons (futuro, opcional)** — Chrome atualizado, telas a partir de 360 px de largura. O layout já deve funcionar neles, mas não são prioridade de teste.

As proteções de acesso simultâneo que já existem continuam valendo (transações, índices únicos, conferência de comanda aberta, proteção contra pagamento duplo). **Não investir em novos cenários com muitos aparelhos**: o caso real é tablet + PC na mesma comanda.

## Como rodar

Desenvolvimento (servidor de desenvolvimento do Flask, com recarga automática):

```
cd C:\tucandeira-bar
python -m pip install -r requirements.txt
python app.py
```

Produção no bar (waitress, acessível pela rede local):

```
cd C:\tucandeira-bar
python servidor.py
```

- O servidor escuta em `0.0.0.0` na porta definida em `config.py` (`PORTA`, padrão 5000).
- No computador servidor: `http://localhost:5000`. Nos tablets: `http://<IP-fixo-do-servidor>:5000` (ex.: `http://192.168.0.10:5000`).
- Testes: `python -m pytest`.
- Dados de demonstração no banco de desenvolvimento: `python scripts/popular_demo.py` (banco sem usuários) ou `python scripts/popular_demo.py --recriar` (guarda um backup e recomeça do zero). Usuários criados: Gerente Demo (1234), Ana (1111), Bruno (2222).
- Regerar as imagens da logo depois de trocar `assets/logo.png`: `python scripts/gerar_imagens.py`.

Dependências: Python 3.14 (instalado: 3.14.4), Flask, waitress, Pillow (gerar ícones do PWA), pytest. SQLite é nativo (módulo `sqlite3`). Tudo listado no `requirements.txt`.

## Funcionalidades do sistema

- Mesas exibidas em grade (livre, ocupada e conta pedida, com cores diferentes) + atendimento de Balcão / Para Viagem
- Comanda por mesa: lançar itens, ver itens, remover itens, fechar conta
- Pagamento em Dinheiro, Débito, Crédito ou PIX, inclusive parcial (cada pessoa paga a sua parte)
- Cardápio com categorias (Bebida, Tira-Gosto, Lanche, Cigarro) e controle de estoque
- Cadastro de produtos
- Relatórios de caixa (dia, semana, mês)

## Versão antiga (Tkinter) — só referência

A versão desktop em Tkinter foi preservada na tag git `v1.0-tkinter` e os arquivos estão em `legado_tkinter/` (`main.py` e `views/`). **Não alterar nem importar nada dessa pasta.** Ela serve apenas como referência do cardápio inicial (6 produtos e 4 categorias, em `legado_tkinter/main.py`, carregados só no banco de desenvolvimento) e do comportamento original.

Falhas do legado que a versão web não pode repetir:

- Estado guardado em variáveis globais / memória: na web tudo fica no banco, pois cada tablet é um cliente separado e o servidor pode reiniciar.
- Comanda que se perde ao fechar a tela: cada item lançado é gravado na hora.
- Estoque baixando ao lançar o item: o estoque só baixa no pagamento.
- Pagamento de balcão que fechava a comanda errada: toda operação recebe o id da comanda.
- Venda que não guardava os itens: a venda grava itens, pagamentos, desconto e usuário.
- Relatório mostrando total geral em vez do período.
- Constantes (cores, caminhos) repetidas em vários arquivos e caminho absoluto da logo.

## Arquitetura

```
tucandeira-bar/
├── app.py               # cria o app Flask (create_app), registra blueprints; roda o servidor de desenvolvimento
├── servidor.py          # inicia o app com waitress (produção, rede local); é também o TucandeiraBar.exe
├── janela_servidor.py   # janela do servidor (Tkinter, sem console): endereços, último backup, parar
├── TucandeiraBar.spec   # receita do PyInstaller (onefile, console=False)
├── config.py            # NUM_MESAS, PORTA, prazos, formas de pagamento, tempo de sessão, caminhos (pathlib)
├── database.py          # conexão SQLite (WAL), transações, criação/migração das tabelas, carga inicial (só desenvolvimento)
├── models/              # dataclasses: Usuario, Produto, Categoria, Comanda, ItemComanda, Venda, ItemVenda, Pagamento, Caixa...
├── services/            # regras de negócio, SEM nenhum import de Flask
│   ├── erros.py         # exceções de regra de negócio (mensagens prontas em português)
│   ├── comum.py         # relógio injetável, validações, auditoria
│   ├── usuarios.py
│   ├── produtos.py
│   ├── caixa.py
│   ├── comandas.py
│   ├── pagamentos.py    # pagamentos, estornos, descontos e fechamento da venda
│   ├── configuracoes.py # configurações do bar (ex.: permitir desconto)
│   ├── formatacao.py    # formatar_moeda()
│   ├── relatorios.py
│   ├── importacao.py    # importação do cardápio por planilha CSV (conferência + gravação numa transação)
│   ├── rede.py          # IPs desta máquina (endereços para os tablets)
│   └── backup.py        # backup ao iniciar, diário (backup_se_preciso) e "Fazer backup agora"
├── routes/              # blueprints Flask: recebem a requisição, chamam services, devolvem HTML/JSON
│   ├── seguranca.py     # sessão, expiração, CSRF, @login_obrigatorio, autorização de gerente do formulário
│   ├── auth.py          # primeiro acesso, login (nome + PIN), trocar usuário, trocar meu PIN
│   ├── mesas.py         # tela de mesas e comandas
│   ├── caixa.py
│   ├── pagamentos.py
│   ├── produtos.py
│   ├── relatorios.py
│   ├── sistema.py       # tela "Sobre" (versão, endereços, backup)
│   └── usuarios.py
├── templates/           # Jinja2 (base.html com o layout comum)
├── static/
│   ├── css/             # CSS próprio
│   ├── js/              # JavaScript simples (sem frameworks pesados)
│   ├── fonts/           # Anton-Regular.woff2 + .ttf + OFL.txt (fonte dos títulos)
│   ├── img/             # logo redimensionada e otimizada para a web
│   ├── icones/          # ícones do PWA gerados a partir de assets/logo.png
│   ├── manifest.webmanifest
│   └── sw.js            # service worker mínimo (só para permitir instalar o PWA)
├── assets/logo.png      # logo original
├── data/tucandeira.db   # banco (não versionar)
├── data/backups/        # backups automáticos (não versionar)
├── scripts/             # gerar_imagens.py, popular_demo.py, gerar_exe.ps1, montar_entrega.py, instalar/atualizar/firewall (.ps1 + .bat)
├── INSTALACAO_BAR.md    # ensaio em casa, instalação no bar, o que levar e treinamento (vai no pacote)
├── VALIDACAO.md         # validação completa opcional para o ensaio em casa (+ validacao_cardapio.csv); fora do pacote
├── legado_tkinter/      # versão antiga, só referência
└── tests/               # pytest para os services (e alguns testes de rotas com o test client do Flask)
```

### Stack

- **Servidor:** Flask. Em produção, waitress no Windows, `host="0.0.0.0"`, porta em `config.py`. O servidor de desenvolvimento do Flask nunca é usado no bar.
- **Banco:** SQLite em `data/tucandeira.db`, com `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON` e `busy_timeout` (ex.: 5000 ms). Uma conexão por requisição (aberta no `g` do Flask e fechada no fim). Toda operação que altera mais de uma tabela roda numa transação única (`BEGIN IMMEDIATE ... COMMIT`, com rollback em erro), pois vários tablets acessam ao mesmo tempo (ex.: dois garçons lançando na mesma comanda, ou um lançando enquanto o caixa recebe o pagamento).
- **Telas:** templates Jinja2 em `templates/`, CSS próprio em `static/css/`, JavaScript simples em `static/js/` (sem React, Vue, jQuery ou similares). Tudo servido localmente — nada de CDN, o bar pode ficar sem internet.
- **Atualização automática:** a tela de mesas consulta o servidor a cada poucos segundos (`INTERVALO_ATUALIZACAO_MESAS` em `config.py`, padrão 5 s) por uma rota JSON e redesenha as mesas, em todos os aparelhos. A tela da comanda aberta também se atualiza, para ver itens lançados por outro garçom. A atualização **pausa quando a aba está em segundo plano** (`document.hidden`, evento `visibilitychange`) e, ao voltar, atualiza na hora e retoma o intervalo.
- **PWA:** `manifest.webmanifest` com `display: "fullscreen"` (ou `standalone`), cores do bar e ícones 192×192 e 512×512 gerados a partir de `assets/logo.png` (script com Pillow), para adicionar à tela inicial do tablet e abrir em tela cheia. Service worker mínimo; o sistema **não** funciona offline (precisa do servidor).
  - **Limitação — contexto seguro:** service worker e "Instalar app" só funcionam em contexto seguro (HTTPS ou `localhost`). Acessando o servidor por `http://192.168.x.x`, o navegador do tablet pode não oferecer "Instalar app" nem abrir em tela cheia. Soluções (detalhadas na etapa de rede do `ROTEIRO.md`): 1ª opção, no Chrome do tablet, liberar o endereço do servidor em `chrome://flags` → "Insecure origins treated as secure"; 2ª opção, usar um navegador de quiosque em tela cheia.
  - **O PWA é opcional:** o sistema precisa funcionar normalmente numa aba comum do navegador, sem o PWA instalado. O registro do service worker só é tentado quando `window.isSecureContext` for verdadeiro e `'serviceWorker' in navigator`, e uma falha nele nunca pode quebrar a página. Nenhuma funcionalidade pode depender do service worker nem do modo tela cheia.

### Interface para tablet e celular

- Pensada para toque em tablet de 10" e em celular: botões e áreas de toque com no mínimo 48×48 px, espaçamento entre botões, fontes legíveis à distância de um braço.
- Nada que dependa de mouse (hover, clique direito, duplo clique) ou de teclado físico. PIN e valores são digitados em teclado numérico na tela; textos curtos (nome do cliente, observação, motivo) usam o teclado virtual do aparelho ou botões de atalho.
- **Todas as telas também com mouse e teclado no PC** (não só a do caixa): mesas, comandas, lançamento de itens, pagamento, produtos e relatórios. Campos de valor e PIN aceitam digitação pelo teclado físico, Enter envia o formulário, e nenhuma ação depende de toque (gestos de deslizar, toque longo).
- Layout responsivo a partir de **360 px de largura** (celular) até o tablet e o computador, em retrato e paisagem (media queries), sem rolagem horizontal.
- **Tela da comanda:** em telas largas (tablet), cardápio e comanda lado a lado; em telas pequenas (celular), cardápio e comanda em **abas** ("Cardápio" / "Comanda (n itens)"). Em qualquer tamanho, o total e o botão "Fechar Conta" ficam sempre visíveis (barra fixa no rodapé).
- Confirmação para ações destrutivas (cancelar item, fechar caixa) e proteção contra toque duplo (botão desativado enquanto a requisição está em andamento).
- Identidade visual mantida: fundo verde `#004d26`, botões pretos, destaque amarelo `#ffcc00`, títulos na fonte **Anton**, logo do bar no topo.
- **Fonte dos títulos (obrigatório):** tablets Android não têm a fonte Impact. Usar a fonte **Anton** (licença livre SIL Open Font License), como arquivo local em `static/fonts/` (`Anton-Regular.woff2`, `Anton-Regular.ttf` e o texto da licença `OFL.txt`), carregada com `@font-face` (`font-display: swap`) e declarada como `font-family: "Anton", Impact, "Arial Narrow Bold", sans-serif` — Impact só como alternativa. Nunca carregar de CDN/Google Fonts.
- Cores das mesas: livre, ocupada e conta pedida, definidas em variáveis CSS num único lugar (`static/css/`).

### Compatibilidade com navegador antigo

- CSS e JavaScript conservadores, escritos à mão, **sem etapa de build no front-end** (sem npm, bundler, transpilador ou pré-processador CSS). Os arquivos de `static/` e `templates/` são servidos exatamente como estão no repositório. Essa regra vale **só para o front-end (HTML, CSS e JS)** — o empacotamento do servidor em `TucandeiraBar.exe` com PyInstaller (ver "Entrega para o bar") é permitido e faz parte da entrega.
- O alvo mínimo é o Chrome do tablet antigo (ver "Aparelhos"). Evitar recursos recentes que ele não suporte, como `:has()`, aninhamento de CSS, container queries, unidades `dvh`/`svh`/`lvh`, `aspect-ratio`, `gap` em flexbox, `inset`, `dialog`, `structuredClone`, optional chaining (`?.`), nullish (`??`), top-level `await` e módulos ES. Preferir: flexbox com margens, media queries, `var` de CSS (custom properties), `fetch` + `then` (ou `XMLHttpRequest` se o Chrome for muito antigo), `addEventListener`.
- Quando usar algo mais novo, ter uma alternativa que funcione: declarar antes o valor antigo (ex.: `height: 100vh;` e depois `height: 100dvh;`), usar `@supports` ou testar no JS (`if ('x' in window)`). O registro do service worker testa `'serviceWorker' in navigator` e `window.isSecureContext` antes de qualquer coisa.
- Fonte Anton em `woff2` com `ttf` como segunda opção no `src` do `@font-face`.

### Páginas leves

- Pouco JavaScript e CSS: um CSS comum e, por tela, só o JS que ela usa. Nada de bibliotecas de ícones ou de componentes; ícones simples em SVG inline ou caracteres.
- Logo redimensionada e otimizada para a web (versões em `static/img/`, geradas por script com Pillow a partir de `assets/logo.png`, no tamanho em que são exibidas), nunca o arquivo original.
- Rotas JSON de atualização devolvem só o necessário (estado das mesas, não a página inteira).

### Banco de dados (esquema)

O esquema completo está em `database.py` (`ESQUEMA_V1`). Pontos que guiam os services:

- Dinheiro sempre em centavos (`..._centavos`). Nome e preço do produto são copiados no item da comanda e da venda.
- **Mesa ocupada** = linha em `comanda_mesas` com `liberada_em IS NULL`; um índice único parcial impede duas comandas na mesma mesa. Transferir e juntar mesas mexem só nessa tabela.
- Status da comanda: `aberta`, `conta_pedida`, `paga`, `unida` (foi juntada a outra, `unida_a`), `cancelada`.
- Cada toque em "+" é uma linha em `itens_comanda` com a própria hora (necessário para a regra dos 2 minutos). Remoções e cancelamentos ficam em `item_ajustes`; a quantidade atual do item já desconta os ajustes.
- **Sem taxa de serviço e sem couvert:** o cliente paga exatamente o preço de tabela dos produtos. Os descontos ficam **na comanda**, porque ela recebe pagamentos antes de fechar. Total = soma dos itens − descontos; já pago = soma dos `pagamentos` não estornados; saldo = total − já pago.
- Ao zerar o saldo, na mesma transação: cria `vendas` + `itens_venda`, baixa o estoque, marca a comanda como `paga` e libera as mesas. `vendas.comanda_id` é único (nunca duas vendas da mesma comanda). Lançar item depois de um pagamento parcial é permitido; remover, cancelar ou dar desconto que deixe o total abaixo do já pago, não.
- Só um caixa com status `aberto` (índice único parcial). Conferência = soma dos pagamentos não estornados do caixa por forma.
- Descontos só em R$ (`descontos.valor_centavos`), com motivo, quem lançou e o gerente que autorizou.
- `configuracoes.permitir_desconto` (`0`/`1`, padrão `0`): só o gerente muda, com registro na auditoria.
- `configuracoes.ambiente` (`desenvolvimento` ou `producao`) é gravado na criação do banco e nunca muda. `desenvolvimento` só quando o banco é criado pelo código-fonte na pasta `data/` do projeto.
- Mudança de estrutura = nova função em `MIGRACOES` (nunca alterar as antigas). O servidor faz backup antes de migrar.

### Regras de arquitetura

- **Services não importam Flask** (nem `request`, `session`, `flash`, `abort`). Recebem dados simples e a conexão/usuário por parâmetro; em caso de erro lançam exceções próprias (ex.: `CaixaFechadoError`, `PermissaoNegadaError`, `PrazoRemocaoExpiradoError`) e a rota decide como responder.
- **Routes não acessam o banco direto** e não contêm regra de negócio: validam a entrada, chamam o service, devolvem template ou JSON.
- **Templates não calculam valores**: totais, saldo, valor por pessoa e troco vêm prontos do service.
- `legado_tkinter/` não é importado por nenhum arquivo.
- Caminhos de arquivo sempre com `pathlib`, definidos só no `config.py`, em dois grupos:
  - **Arquivos do programa** (templates, static, assets): relativos a `Path(__file__).resolve().parent`; no executável do PyInstaller, relativos a `sys._MEIPASS` (detectar com `getattr(sys, "frozen", False)`).
  - **Pasta de dados** (`PASTA_DADOS`: banco, backups, `secret_key`, logs): separada do programa. No desenvolvimento, `data/` dentro do projeto; no executável, `C:\TucandeiraBar\dados\`. Pode ser trocada pela variável de ambiente `TUCANDEIRA_DADOS`. Nenhum código grava dentro da pasta do programa.
- Valores monetários exibidos no formato `R$ 1.234,56`. Uma única função `formatar_moeda()` (registrada também como filtro Jinja2 `moeda`). Valores guardados no banco em centavos (inteiro), para evitar erro de arredondamento.
- Datas gravadas no banco em ISO (`YYYY-MM-DD HH:MM:SS`), horário local do servidor.
- O estado das mesas vem do banco: mesa ocupada = existe comanda aberta para ela; "conta pedida" é um status da comanda.
- Concorrência: antes de alterar uma comanda, o service confere se ela ainda está aberta (outro tablet pode ter acabado de pagar ou transferir) e lança exceção se não estiver. Ações de lançar/pagar são idempotentes contra toque duplo.

### Segurança

- Uso **apenas na rede local do bar**. Nunca expor à internet (sem redirecionamento de porta no roteador, sem túneis). A regra de firewall do Windows libera a porta só para a rede privada.
- Login: tocar no **nome** do usuário e digitar o **PIN** de 4 dígitos. PINs podem se repetir entre usuários, e o sistema **nunca** informa que um PIN "já está em uso". Sessão Flask (cookie assinado com `SECRET_KEY` gerada na instalação e guardada na pasta de dados, fora do git — `data/secret_key` no desenvolvimento). A sessão expira após um tempo sem uso (`TEMPO_SESSAO_MINUTOS` em `config.py`, padrão 15) e volta para a tela de login.
- Ações de gerente pedem a autorização **na hora** (escolher o gerente na lista e digitar o PIN dele), mesmo que o gerente já esteja logado no aparelho; a autorização vale só para aquela ação e registra qual gerente autorizou.
- Limite de tentativas de PIN erradas: bloqueio de 1 minuto após 5 erros seguidos, contado por usuário e por aparelho (em memória; zera se o servidor reiniciar).
- PIN guardado com hash + salt (`hashlib.pbkdf2_hmac`), nunca em texto puro.
- Formulários com proteção CSRF (token na sessão). Toda entrada validada no servidor, nunca só no JavaScript.
- **Tela de usuários:** gerente logado abre direto; operador abre só com autorização de um gerente, válida por `ACESSO_TELA_USUARIOS_MINUTOS` (5). Cada alteração (cadastrar, editar, trocar PIN, desativar) pede a autorização na hora, mesmo para gerente logado.
- **Nas telas:** formulário com `data-exige-gerente="texto da ação"` abre o quadro de autorização antes de enviar; a rota lê `gerente_id` + `pin_gerente` com `autorizacao_do_formulario()`. Atualizações automáticas mandam o cabeçalho `X-Atualizacao-Automatica` para não renovar a sessão.

## Regras de trabalho

- Trabalhar **uma etapa por vez** conforme o `ROTEIRO.md`. Ao terminar uma etapa, rodar **todos** os testes (`python -m pytest`) e o servidor, resumir o que mudou, entregar um roteiro curto de teste manual e aguardar confirmação antes da próxima.
- **Testes automáticos:** manter os existentes e rodá-los ao fim de cada etapa. Daqui para frente, escrever testes automáticos **só para regras de dinheiro, estoque, caixa ou acesso simultâneo**. Telas e rotas são testadas manualmente, com um roteiro curto de teste no fim de cada etapa (passos numerados: o que tocar e o que deve aparecer).
- **Roteiro de teste manual:** no máximo **5 itens** por etapa, só com o que os testes automáticos não cobrem: visual, fluxo na tela e atualização entre aparelhos. Regras de cálculo já testadas no pytest não entram no roteiro.
- **Plurais:** nunca escrever "pessoa(s)", "minuto(s)" etc. Usar `plural()` de `services/formatacao.py` (também filtro Jinja `plural`): "1 pessoa", "4 pessoas".
- Fazer commit no git ao fim de cada etapa, com mensagem em português.
- Perguntar antes de apagar arquivos ou mudar o comportamento de alguma funcionalidade existente.
- Nunca apagar nem recriar o banco com dados reais (`data/tucandeira.db` no desenvolvimento, `C:\TucandeiraBar\dados\tucandeira.db` no bar); alterações de estrutura devem preservar os dados (migração por `PRAGMA user_version`).
- Manter a identidade visual (fundo verde `#004d26`, botões pretos, destaque amarelo `#ffcc00`, fonte Anton local nos títulos, logo).
- Testar cada tela no **Chrome do tablet antigo** (retrato e paisagem) e no **navegador do PC servidor** — não só no modo de dispositivo do navegador, que serve para o desenvolvimento mas não substitui o tablet real. Celular (a partir de 360 px) é teste opcional. A partir da Etapa 5, o roteiro de teste manual de cada etapa inclui o **teste no PC com mouse e teclado**: fazer as operações da etapa só pelo PC em `http://localhost:5000`, como se o tablet não tivesse conectado.

## Decisões tomadas

- **Produto sem estoque:** avisar e permitir a venda. O estoque pode ficar negativo, e isso aparece destacado nos relatórios.
- **Preço de tabela:** o bar **não** cobra taxa de serviço nem couvert artístico. O cliente paga exatamente a soma dos produtos, menos um eventual desconto (ver abaixo).
- **Desconto:** opcional, a critério do dono, e só em R$ (sem percentual). A configuração "permitir desconto" vem **desligada** e só o gerente liga ou desliga (registrado na auditoria). Desligada, o botão de desconto não aparece nas telas e o service recusa qualquer desconto (`DescontoNaoPermitidoError`). Ligada, cada desconto exige motivo e PIN de gerente, não pode passar da conta nem deixá-la abaixo do já pago. Um desconto lançado por engano pode ser removido pelo gerente (inclusive com a configuração desligada), com registro na auditoria.
- **Pagamento dividido e parcial:** uma conta pode ser paga com formas diferentes (ex.: parte PIX, parte dinheiro) e aos poucos (uma pessoa paga a parte dela e vai embora). A comanda mostra total, já pago e saldo; a venda é fechada quando o saldo chega a zero. Cada pagamento registra quem recebeu.
- **Formas de pagamento:** Dinheiro, Débito, Crédito e PIX (também separadas na conferência do caixa).
- **Estorno de pagamento:** enquanto a comanda não estiver paga, um pagamento lançado errado pode ser estornado, com motivo e PIN de gerente. O pagamento não é apagado: fica marcado como estornado e deixa de contar no já pago e na conferência do caixa.
- **Comanda cancelada:** sem itens (ou com todos removidos/cancelados) e sem pagamentos, o operador cancela sozinho, liberando a mesa. Com itens, o cancelamento exige motivo e PIN de gerente. Comanda cancelada não gera venda, não baixa estoque e não bloqueia o fechamento do caixa.
- **Fechamento do caixa:** bloqueado enquanto houver comandas abertas ou com conta pedida; o sistema mostra quais são.
- **Estoque:** entradas, perdas e ajustes de contagem ficam em `movimentos_estoque`, com motivo, usuário e data. Perda e ajuste exigem PIN de gerente. A baixa por venda vem de `itens_venda`.
- **Número de mesas:** configurável no `config.py` (`NUM_MESAS`), padrão 8.
- **Remover x cancelar item:** o operador pode remover um item sem PIN até 2 minutos depois de lançá-lo (prazo configurável no `config.py`). Depois disso, só por cancelamento, que exige motivo e PIN de gerente e fica registrado.
- **Plataforma:** aplicação web na rede local (Flask + waitress), acessada por tablets e pelo computador do caixa. A versão Tkinter foi abandonada (tag `v1.0-tkinter`).
- **Sangria:** não pode ser maior que o dinheiro que deveria estar no caixa (fundo + pagamentos em dinheiro + suprimentos − sangrias).
- **Desativar categoria:** só se ela não tiver produtos ativos, para nenhum produto sumir do cardápio sem querer.
- **Balcão:** não pode haver duas comandas de balcão abertas com o mesmo nome de cliente (ex.: usar "João 2").
- **Aviso de estoque ao lançar:** considera o estoque menos o que já está lançado nas comandas abertas (o estoque só baixa no pagamento).
- **Transferir mesa junta:** transfere só a mesa escolhida; as outras mesas continuam juntas na mesma comanda.
- **Instalação no bar 100% zerada (24/10/2026):** o banco de produção (criado pelo executável) nasce sem usuários, sem vendas e sem nenhum produto ou categoria. O primeiro acesso cria o gerente e o cardápio entra só pela importação da planilha do dono. A carga inicial do cardápio do legado existe só no banco de desenvolvimento. O `modelo_cardapio.csv` do pacote vem só com o cabeçalho.
- **Sem noite de validação no bar (24/10/2026):** `VALIDACAO.md` e `validacao_cardapio.csv` ficam só no repositório, para o ensaio em casa, e não vão no pacote de entrega. O plano é: ensaio no notebook → instalação no bar → treinamento rápido da equipe, tudo descrito no `INSTALACAO_BAR.md` (que vai no pacote). O `COMECAR_BANCO_LIMPO.bat` é opcional: só se houver testes no computador do bar antes da primeira venda.

## Requisitos do sistema

### Versão 2.0

- **Usuários:** login tocando no nome e digitando o PIN de 4 dígitos; perfis Operador e Gerente. Ações que exigem PIN de gerente: cancelar item, cancelar comanda com itens, ligar/desligar e dar desconto, estornar pagamento, sangria, perda e ajuste de estoque, fechar caixa, cadastrar usuários. Toda operação registra quem fez e quando.
- **Caixa:** o sistema só permite vendas com caixa aberto. Abertura com valor inicial (fundo de troco). Sangria e suprimento com motivo. Fechamento com conferência: valor esperado x valor contado por forma de pagamento (dinheiro, débito, crédito, PIX), mostrando a diferença. Não fecha com comandas abertas ou com conta pedida.
- **Mesas:** status livre, ocupada e "conta pedida" (cores diferentes); número de pessoas na mesa; transferir comanda para outra mesa; juntar mesas.
- **Comandas:** balcão com várias comandas abertas, identificadas pelo nome do cliente; adicionar e remover itens; observação por item; cancelamento de item já lançado exige motivo e PIN de gerente e fica registrado; cancelamento da comanda inteira (regra acima).
- **Pagamento:** preço de tabela, sem taxa de serviço nem couvert; desconto opcional só em R$ (regra acima); dividir entre formas de pagamento; pagamento parcial com total, já pago e saldo; estorno de pagamento; mostrar o valor dividido igualmente por pessoa; cálculo de troco em dinheiro.
- **Produtos e estoque:** cadastrar, editar, desativar; categorias editáveis; estoque mínimo por produto, com alerta; movimentos de estoque registrados (entrada de mercadoria, perda, ajuste de contagem); importação do cardápio por planilha CSV (modelo com o cardápio atual, conferência linha a linha antes de gravar, PIN do gerente).
- **Relatórios:** vendas por período (dia, semana, mês, intervalo personalizado); total por forma de pagamento; produtos mais vendidos; cancelamentos e descontos com responsável e motivo; produtos com estoque negativo ou abaixo do mínimo; histórico de fechamentos de caixa; exportar para CSV.
- **Segurança dos dados:** backup automático do banco ao iniciar o servidor (e uma vez por dia enquanto ele estiver rodando), mantendo os 7 últimos.
- **Dados de demonstração:** comando separado (`python scripts/popular_demo.py`) que popula o banco de desenvolvimento com usuários, produtos e dias de caixas e vendas no passado, para testar telas e relatórios. Recusa-se a rodar se o banco não for o de desenvolvimento.
- **Acesso simultâneo:** vários tablets usando o sistema ao mesmo tempo, sem perder nem duplicar lançamentos (transações no banco), com a tela de mesas atualizada sozinha em todos eles.
- **Tela de caixa:** uma tela de caixa (abertura, sangria/suprimento, pagamentos, fechamento) que também funcione bem no navegador do próprio computador servidor, com mouse e teclado, além do toque no tablet.

- **Entrega para o bar:**
  - Pacote de instalação com PyInstaller: um `TucandeiraBar.exe` do servidor (waitress + Flask, com templates, static e assets embutidos), que roda sem Python instalado no computador do bar.
  - Banco, backups, `secret_key` e logs numa pasta de dados separada do programa (`C:\TucandeiraBar\dados\`). Atualizar o sistema é só trocar o executável (`C:\TucandeiraBar\programa\TucandeiraBar.exe`), sem tocar nos dados; o banco é migrado automaticamente (`PRAGMA user_version`) depois de um backup.
  - O servidor inicia junto com o Windows.
  - Ao iniciar, mostra na tela o endereço completo para digitar nos tablets e celulares (ex.: `http://192.168.0.10:5000`), numa janela própria (Tkinter), sem depender de janela de console (que trava com um clique no modo QuickEdit).
  - README com o passo a passo de instalação e de atualização.

### Versão 2.1 (futuro — NÃO implementar agora)

- Impressão de comanda e cupom não fiscal em impressora térmica.
- Emissão de NFC-e via serviço terceirizado.
- Mais de um servidor ou filiais com dados sincronizados.
- Cardápio digital por QR Code.
