# Tucandeira Rock Bar — Sistema de Gestão para Bares

Sistema web para gestão de bar: mesas, comandas, pagamentos, estoque, controle de caixa e relatórios. Feito em Python com Flask e banco de dados SQLite, funciona só na rede local do bar, sem precisar de internet.

## Como o bar usa o sistema

- **PC servidor (caixa):** um computador com Windows roda o sistema e é usado no caixa, com mouse e teclado, em `http://localhost:5000`.
- **Tablet Android do garçom:** um tablet Android antigo, reaproveitado, abre o sistema pelo Chrome no Wi-Fi do bar para lançar pedidos nas mesas.
- **Celulares Android (opcional, futuro):** os garçons poderão usar o próprio celular da mesma forma. O layout já funciona a partir de 360 px de largura.
- **Plano B:** se o tablet não conectar, o bar inteiro é operado pelo PC, sem Wi-Fi e sem internet (veja "Solução de problemas").

## Status

Versão 2.0 (web) em desenvolvimento. O andamento detalhado está no `ROTEIRO.md`.

Etapas concluídas:

- ✅ Etapa 0 — Preparação e segurança
- ✅ Etapa 0.1 — Mudança de plataforma para web
- ✅ Etapa 1 — Estrutura Flask, configuração, banco e backup
- ✅ Etapa 2 — Models e services com testes
- ✅ Etapa 2b — Pagamentos (regras de negócio)
- ✅ Etapa 3 — Login por PIN e usuários
- ✅ Etapa 4 — Controle de caixa
- ✅ Etapa 5 — Tela de mesas e comandas
- ✅ Etapa 6 — Tela de pagamento

Próximas etapas:

- Etapa 7 — Produtos e estoque
- Etapa 8 — Relatórios
- Etapa 9 — Acesso pela rede, PWA e teste em tablet real
- Etapa 10 — Backup automático, executável, início com o Windows e entrega

> A versão desktop antiga (Tkinter) está preservada na tag `v1.0-tkinter` e na pasta `legado_tkinter/`, apenas como referência.

## Funcionalidades (versão 2.0)

- **Tablet e PC ao mesmo tempo:** o garçom lança pelo tablet e o caixa recebe pelo PC, inclusive na mesma comanda, sem perder nem duplicar lançamentos; as telas de mesas e de comanda se atualizam sozinhas nos dois aparelhos.
- **Feito para toque:** botões grandes, teclado numérico na tela, funciona em retrato e paisagem. Funciona numa aba comum do navegador e, opcionalmente, pode ser instalado na tela inicial do tablet para abrir em tela cheia (PWA — veja "Abrir como aplicativo").
- **Usuários:** login tocando no nome e digitando o PIN de 4 dígitos, perfis Operador e Gerente, sessão que expira após um tempo sem uso. Ações sensíveis (cancelar item ou comanda, ligar/desligar e dar desconto, estornar pagamento, sangria, perda e ajuste de estoque, fechar caixa, cadastrar usuários) pedem a autorização do gerente na hora. Toda operação registra quem fez e quando.
- **Caixa:** abertura com fundo de troco, sangria e suprimento com motivo, fechamento com conferência (valor esperado x valor contado em dinheiro, débito, crédito e PIX), só depois de todas as comandas pagas ou canceladas. Vendas só com caixa aberto. A tela de caixa funciona também no navegador do computador servidor.
- **Mesas:** número de mesas configurável (padrão 8), status livre, ocupada e conta pedida, número de pessoas, transferir comanda e juntar mesas.
- **Comandas:** balcão / para viagem com várias comandas identificadas pelo nome do cliente, observação por item. Item removido sem PIN até 2 minutos após o lançamento; depois disso, só cancelamento com motivo e PIN de gerente.
- **Pagamento:** o cliente paga o preço de tabela dos produtos (sem taxa de serviço nem couvert), desconto opcional em R$ (desligado por padrão; o gerente decide se o bar usa e autoriza cada um, com motivo), divisão entre Dinheiro, Débito, Crédito e PIX, pagamento parcial (cada um paga a sua parte, com saldo sempre visível), estorno de pagamento lançado errado, valor por pessoa e cálculo de troco.
- **Produtos e estoque:** cadastro, edição e desativação, categorias editáveis, estoque mínimo com alerta, entrada de mercadoria, perda e ajuste de contagem. Produto sem estoque pode ser vendido (com aviso) e aparece destacado nos relatórios.
- **Relatórios:** vendas por dia, semana, mês ou intervalo, total por forma de pagamento, produtos mais vendidos, cancelamentos e descontos, estoque negativo ou abaixo do mínimo, histórico de fechamentos de caixa e exportação para CSV.
- **Segurança dos dados:** backup automático do banco, mantendo os 7 últimos.

## Planos para a versão 2.1

- Impressão de comanda e cupom não fiscal em impressora térmica
- Emissão de NFC-e via serviço terceirizado
- Mais de um servidor ou filiais com dados sincronizados
- Cardápio digital por QR Code

## Tecnologias

- Python 3.14
- Flask (aplicação web) e waitress (servidor de produção no Windows)
- Jinja2 (templates), CSS próprio e JavaScript simples, sem frameworks pesados
- SQLite em modo WAL (banco de dados local, módulo `sqlite3`)
- Pillow (geração dos ícones do PWA)
- Fonte Anton (licença OFL), incluída em `static/fonts/`
- pytest (testes)

## Requisitos

- **Computador servidor:** Windows 10 ou superior, Python 3.14 (instalador oficial do python.org), conectado à rede do bar (de preferência por cabo) e com IP fixo.
- **Navegador do PC servidor:** Chrome ou Edge atualizado.
- **Tablet e celulares:** Android com o navegador **Chrome**, inclusive versões antigas (o sistema foi escrito para funcionar em tablets reaproveitados). Celulares com tela a partir de 360 px de largura. Safari, iPhone e iPad não são suportados.
- Os aparelhos precisam estar no mesmo Wi-Fi do computador servidor.
- Não precisa de internet para funcionar — só da rede local.

## Instalação no bar

O passo a passo de instalação no computador do bar com o executável `TucandeiraBar.exe` (sem precisar de Python), com os dados em `C:\TucandeiraBar\dados\` e início automático com o Windows, entra neste README na Etapa 10.

## Para desenvolvedores

### Instalar

```
git clone https://github.com/marcianocamposgit/sistema_tucandeira-bar.git
cd sistema_tucandeira-bar
python -m pip install -r requirements.txt
```

O banco de dados é criado automaticamente em `data/tucandeira.db` na primeira execução, já com o cardápio inicial. No primeiro acesso, o sistema pede para criar o usuário gerente. Para começar com o banco limpo, basta **não** rodar o comando de dados de demonstração (abaixo).

### Iniciar o servidor

Uso no bar (servidor waitress, acessível pela rede local):

```
python servidor.py
```

Ao iniciar, o console mostra o endereço para acessar, por exemplo `http://192.168.0.10:5000`. A porta pode ser alterada em `config.py` (`PORTA`).

Desenvolvimento (servidor do Flask com recarga automática — não usar no bar):

```
python app.py
```

Atalho para desenvolvedores no Windows: `iniciar.bat`, na raiz do projeto, encerra um servidor anterior que esteja usando a porta 5000, abre o navegador em `http://localhost:5000` e inicia `python servidor.py` (dá para abrir com dois cliques). Precisa do Python instalado; não é o instalador do bar.

### Testes e dados de demonstração

Para rodar os testes:

```
python -m pytest
```

Para encher o banco de **desenvolvimento** com dados de demonstração (usuários, produtos e dias de vendas no passado), o comando se recusa a rodar num banco de produção:

```
python scripts/popular_demo.py            # num banco ainda sem usuários
python scripts/popular_demo.py --recriar   # guarda um backup e recomeça do zero
python scripts/popular_demo.py --recriar --sem-movimento-hoje   # só o histórico: hoje sem caixa aberto nem comandas
```

Usuários de demonstração (nome / PIN): Gerente Demo / 1234, Ana / 1111, Bruno / 2222.

> ⚠️ **Os PINs de demonstração nunca devem ser usados no bar.** Eles estão publicados aqui e servem só para testar no computador de desenvolvimento. No bar, cada pessoa cria o seu próprio PIN.

## Como acessar

- **No próprio computador servidor (caixa):** abra o navegador em `http://localhost:5000`, toque (ou clique) no seu nome e digite o PIN de 4 dígitos.
- **Nos tablets:**
  1. Conecte o tablet ao Wi-Fi do bar (a mesma rede do computador servidor).
  2. Abra o navegador e digite o endereço mostrado no console do servidor, ex.: `http://192.168.0.10:5000`.
  3. Toque no seu nome e digite o seu PIN de 4 dígitos no teclado da tela.
  4. Pronto: o sistema funciona normalmente numa aba comum do navegador. Instalar como app é opcional.

### Abrir como aplicativo em tela cheia (opcional)

O navegador só oferece "Instalar app" e o modo tela cheia em conexões seguras (HTTPS ou `localhost`). Como os tablets acessam por `http://192.168.x.x`, isso pode não aparecer. Duas formas de resolver:

1. **Chrome no tablet Android (primeira opção):**
   1. Abra `chrome://flags` na barra de endereço.
   2. Procure **Insecure origins treated as secure**, mude para **Enabled** e digite o endereço do servidor (ex.: `http://192.168.0.10:5000`).
   3. Toque em **Relaunch**. Abra o sistema e use o menu ⋮ → **Instalar app** / **Adicionar à tela inicial**. O ícone da logo do bar aparece na tela inicial.
   4. Repita em cada tablet. Se o IP ou a porta do servidor mudarem, é preciso refazer.
2. **Navegador de quiosque (segunda opção):** instale um navegador de quiosque em tela cheia (ex.: Fully Kiosk Browser, no Android) e configure o endereço do servidor como página inicial. Útil quando o Chrome do tablet não aceitar a configuração acima.

## Solução de problemas

### O tablet não conectou: continue pelo PC do caixa

O atendimento não para. O computador servidor faz tudo sozinho, **sem Wi-Fi e sem internet**:

1. No computador servidor, abra o navegador em `http://localhost:5000` (com o servidor rodando).
2. Clique no seu nome, digite o PIN e use o sistema normalmente com mouse e teclado: mesas, comandas, lançamento de itens, pagamento e caixa.
3. Nada se perde: quando o tablet voltar a conectar, ele mostra as mesas e comandas lançadas pelo PC.
4. Com o movimento mais calmo, siga o diagnóstico abaixo para descobrir por que o tablet não conectou.

### O tablet ou o celular não abre o sistema

Siga os passos na ordem; cada um elimina uma causa.

1. **O servidor está rodando?** No próprio computador servidor, abra `http://localhost:5000`. Se não abrir, o problema é no servidor (veja a janela/console do servidor).
2. **O servidor responde pelo IP da rede?** Ainda no computador servidor, abra `http://<IP-do-servidor>:5000` (ex.: `http://192.168.0.10:5000`). Se não abrir, confira o IP com `ipconfig` e se o servidor foi iniciado com `python servidor.py` (o `app.py` só escuta em `localhost`).
3. **Mesma rede?** O tablet precisa estar no mesmo Wi-Fi do servidor (não na rede de visitantes nem nos dados móveis). Confira também se o IP do servidor não mudou (por isso o IP fixo).
4. **Firewall do Windows:** a porta precisa estar liberada para redes **Privadas** (script da Etapa 9) e a rede do bar precisa estar marcada como **Privada** no Windows.
5. **Isolamento de clientes no roteador:** se o tablet abre a página do roteador (ex.: `http://192.168.1.1`) mas não alcança o computador servidor em nenhuma porta — mesmo com o firewall do Windows desligado —, o roteador está impedindo que os aparelhos conversem entre si. É comum em roteadores de operadora e em redes de visitantes. O nome da opção varia: "Isolamento de AP", "AP Isolation", "Client Isolation", "Isolamento de clientes", "Wireless isolation".
   - **Solução:** desligar essa opção no roteador (na rede usada pelo bar, não na de visitantes) ou usar um roteador próprio para o sistema.
   - **Teste rápido para confirmar:** ligue o **Hotspot móvel** do Windows no computador servidor (Configurações → Rede e Internet → Hotspot móvel), conecte o tablet nesse hotspot e acesse `http://<IP-do-servidor-no-hotspot>:5000` (normalmente `http://192.168.137.1:5000`). Se funcionar pelo hotspot, o problema é o roteador. O hotspot serve só como teste: não é a solução definitiva para o bar.

## Segurança

O sistema foi feito para uso **apenas na rede local do bar**. Não abra a porta no roteador nem exponha o servidor à internet. A sessão expira após um tempo sem uso, e as ações de gerente sempre pedem o PIN do gerente na hora.

## Estrutura de pastas

```
tucandeira-bar/
├── app.py               # cria o app Flask (e roda o servidor de desenvolvimento)
├── servidor.py          # inicia o sistema com waitress na rede local
├── config.py            # número de mesas, porta, prazos, formas de pagamento, tempo de sessão, caminhos
├── database.py          # conexão SQLite (WAL), transações e criação das tabelas
├── models/              # classes de dados (Produto, Comanda, Venda...)
├── services/            # regras de negócio (usuários, produtos, caixa, comandas, pagamentos, relatórios, backup)
├── routes/              # rotas Flask (blueprints)
├── templates/           # páginas HTML (Jinja2)
├── static/              # CSS, JavaScript, fonte Anton, ícones e manifest do PWA
├── data/                # banco de dados e backups (não versionados)
├── assets/              # logo e imagens
├── scripts/            # utilitários (imagens da logo, dados de demonstração, instalação)
├── legado_tkinter/      # versão antiga em Tkinter (só referência)
└── tests/               # testes automatizados (pytest)
```

> A estrutura acima é a da versão 2.0. Durante o desenvolvimento, alguns arquivos ainda não existem — veja o andamento no `ROTEIRO.md`.

## Autor

Marciano Campos
