# Tucandeira Rock Bar — Sistema de Gestão para Bares

Sistema web para gestão de bar: mesas, comandas, pagamentos, estoque, controle de caixa e relatórios. Um computador do bar funciona como servidor e os garçons usam tablets pelo navegador, na rede Wi-Fi local. Feito em Python com Flask e banco de dados SQLite.

**Status:** em desenvolvimento — versão 2.0 (web) em andamento. Veja o andamento no `ROTEIRO.md`.

> A versão desktop antiga (Tkinter) está preservada na tag `v1.0-tkinter` e na pasta `legado_tkinter/`, apenas como referência.

## Funcionalidades (versão 2.0)

- **Vários tablets ao mesmo tempo:** garçons lançam pedidos de qualquer tablet, inclusive na mesma comanda; a tela de mesas se atualiza sozinha em todos os aparelhos.
- **Feito para toque:** botões grandes, teclado numérico na tela, funciona em retrato e paisagem. Funciona numa aba comum do navegador e, opcionalmente, pode ser instalado na tela inicial do tablet para abrir em tela cheia (PWA — veja "Abrir como aplicativo").
- **Usuários:** login tocando no nome e digitando o PIN de 4 dígitos, perfis Operador e Gerente, sessão que expira após um tempo sem uso. Ações sensíveis (cancelar item ou comanda, dar desconto, estornar pagamento, sangria, perda e ajuste de estoque, fechar caixa, cadastrar usuários) pedem a autorização do gerente na hora. Toda operação registra quem fez e quando.
- **Caixa:** abertura com fundo de troco, sangria e suprimento com motivo, fechamento com conferência (valor esperado x valor contado em dinheiro, débito, crédito e PIX), só depois de todas as comandas pagas ou canceladas. Vendas só com caixa aberto. A tela de caixa funciona também no navegador do computador servidor.
- **Mesas:** número de mesas configurável (padrão 8), status livre, ocupada e conta pedida, número de pessoas, transferir comanda e juntar mesas.
- **Comandas:** balcão / para viagem com várias comandas identificadas pelo nome do cliente, observação por item. Item removido sem PIN até 2 minutos após o lançamento; depois disso, só cancelamento com motivo e PIN de gerente.
- **Pagamento:** o cliente paga o preço de tabela dos produtos (sem taxa de serviço nem couvert), desconto em R$ ou % (com motivo e PIN de gerente), divisão entre Dinheiro, Débito, Crédito e PIX, pagamento parcial (cada um paga a sua parte, com saldo sempre visível), estorno de pagamento lançado errado, valor por pessoa e cálculo de troco.
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
- **Tablets:** qualquer tablet com navegador atualizado (Chrome, Edge, Safari), conectado ao Wi-Fi do bar.
- Não precisa de internet para funcionar — só da rede local.

## Como instalar

No computador servidor:

```
git clone https://github.com/marcianocamposgit/sistema_tucandeira-bar.git
cd sistema_tucandeira-bar
python -m pip install -r requirements.txt
```

O banco de dados é criado automaticamente em `data/tucandeira.db` na primeira execução, já com o cardápio inicial. No primeiro acesso, o sistema pede para criar o usuário gerente.

## Como iniciar o servidor

Uso no bar (servidor waitress, acessível pela rede local):

```
python servidor.py
```

Ao iniciar, o console mostra o endereço para acessar, por exemplo `http://192.168.0.10:5000`. A porta pode ser alterada em `config.py` (`PORTA`).

Desenvolvimento (servidor do Flask com recarga automática — não usar no bar):

```
python app.py
```

Para rodar os testes:

```
python -m pytest
```

Para encher o banco de **desenvolvimento** com dados de demonstração (usuários, produtos e dias de vendas no passado), o comando se recusa a rodar num banco de produção:

```
python scripts/popular_demo.py            # num banco ainda sem usuários
python scripts/popular_demo.py --recriar   # guarda um backup e recomeça do zero
```

Usuários de demonstração (nome / PIN): Gerente Demo / 1234, Ana / 1111, Bruno / 2222.

## Como acessar

- **No próprio computador servidor (caixa):** abra o navegador em `http://localhost:5000`.
- **Nos tablets:**
  1. Conecte o tablet ao Wi-Fi do bar (a mesma rede do computador servidor).
  2. Abra o navegador e digite o endereço mostrado no console do servidor, ex.: `http://192.168.0.10:5000`.
  3. Entre com o seu PIN.
  4. Pronto: o sistema funciona normalmente numa aba comum do navegador. Instalar como app é opcional.

### Abrir como aplicativo em tela cheia (opcional)

O navegador só oferece "Instalar app" e o modo tela cheia em conexões seguras (HTTPS ou `localhost`). Como os tablets acessam por `http://192.168.x.x`, isso pode não aparecer. Duas formas de resolver:

1. **Chrome no tablet Android (primeira opção):**
   1. Abra `chrome://flags` na barra de endereço.
   2. Procure **Insecure origins treated as secure**, mude para **Enabled** e digite o endereço do servidor (ex.: `http://192.168.0.10:5000`).
   3. Toque em **Relaunch**. Abra o sistema e use o menu ⋮ → **Instalar app** / **Adicionar à tela inicial**. O ícone da logo do bar aparece na tela inicial.
   4. Repita em cada tablet. Se o IP ou a porta do servidor mudarem, é preciso refazer.
2. **Navegador de quiosque (segunda opção):** instale um navegador de quiosque em tela cheia (ex.: Fully Kiosk Browser, no Android) e configure o endereço do servidor como página inicial. Útil também no iPad ou quando o Chrome não aceitar a configuração acima.

### Se o tablet não conseguir acessar

- Confira se o tablet e o servidor estão na mesma rede Wi-Fi.
- Confira se o IP do servidor não mudou (por isso o IP fixo).
- Confira se a porta está liberada no Firewall do Windows para redes **privadas** (o script de liberação é criado na Etapa 9 do roteiro) e se a rede do bar está marcada como Privada no Windows.

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
