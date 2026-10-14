# Tucandeira Rock Bar — Sistema de Gestão para Bares

Sistema desktop para gestão de bar: mesas, comandas, pagamentos, estoque, controle de caixa e relatórios. Feito em Python com interface Tkinter e banco de dados SQLite local.

**Status:** em desenvolvimento — versão 2.0 em andamento.

## Funcionalidades (versão 2.0)

- **Usuários:** login por PIN de 4 dígitos, perfis Operador e Gerente. Ações sensíveis (cancelar item, dar desconto, remover taxa de serviço, sangria, fechar caixa, cadastrar usuários) exigem PIN de gerente. Toda operação registra quem fez e quando.
- **Caixa:** abertura com fundo de troco, sangria e suprimento com motivo, fechamento com conferência (valor esperado x valor contado por forma de pagamento). Vendas só com caixa aberto.
- **Mesas:** número de mesas configurável (padrão 8), status livre, ocupada e conta pedida, número de pessoas, transferir comanda e juntar mesas.
- **Comandas:** balcão / para viagem com várias comandas identificadas pelo nome do cliente, observação por item, cancelamento de item com motivo e PIN de gerente.
- **Pagamento:** taxa de serviço de 10% nas mesas (removível pelo gerente), couvert artístico por pessoa em dia de show, desconto em R$ ou %, divisão entre Dinheiro, Cartão e PIX, valor por pessoa e cálculo de troco.
- **Produtos e estoque:** cadastro, edição e desativação, categorias editáveis, estoque mínimo com alerta, entrada de mercadoria. Produto sem estoque pode ser vendido (com aviso) e aparece destacado nos relatórios.
- **Relatórios:** vendas por dia, semana, mês ou intervalo, total por forma de pagamento, produtos mais vendidos, cancelamentos e descontos, estoque negativo ou abaixo do mínimo, histórico de fechamentos de caixa e exportação para CSV.
- **Segurança dos dados:** backup automático do banco ao abrir o sistema, mantendo os 7 últimos.

## Planos para a versão 2.1

- Impressão de comanda e cupom não fiscal em impressora térmica
- Emissão de NFC-e via serviço terceirizado
- Uso em vários computadores em rede
- Cardápio digital por QR Code

## Tecnologias

- Python 3.14
- Tkinter (interface gráfica)
- SQLite (banco de dados local, módulo `sqlite3`)
- Pillow (imagens)
- pytest (testes)

## Requisitos

- Windows 10 ou superior
- Python 3.14 com Tkinter (já incluso no instalador oficial do python.org)

## Como instalar e rodar

```
git clone https://github.com/marcianocamposgit/sistema_tucandeira-bar.git
cd sistema_tucandeira-bar
python -m pip install -r requirements.txt
python main.py
```

O banco de dados é criado automaticamente em `data/tucandeira.db` na primeira execução.

## Estrutura de pastas

```
tucandeira-bar/
├── main.py              # ponto de entrada: inicializa o banco e abre a tela principal
├── config.py            # cores, fontes, número de mesas, caminhos
├── database.py          # conexão SQLite e criação das tabelas
├── models/              # classes de dados (Produto, Comanda, Venda...)
├── services/            # regras de negócio (usuários, produtos, caixa, comandas, pagamentos, relatórios, backup)
├── views/               # telas Tkinter
├── data/                # banco de dados e backups (não versionados)
├── assets/              # logo e imagens
└── tests/               # testes automatizados (pytest)
```

> A estrutura acima é a da versão 2.0. Durante o desenvolvimento, alguns arquivos ainda não existem — veja o andamento no `ROTEIRO.md`.

## Autor

Marciano Campos
