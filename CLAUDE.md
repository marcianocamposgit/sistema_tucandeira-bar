# Tucandeira Rock Bar — Sistema de Gestão

Sistema desktop de gestão para bar, em Python + Tkinter. Autor: Marciano Campos.
Todo o código, comentários, nomes de variáveis e mensagens ao usuário devem ser em **português do Brasil**.

## Como rodar

```
cd C:\tucandeira-bar
python main.py
```

Dependências: Python 3.14 (instalado: 3.14.4), Tkinter (nativo), Pillow (`pip install pillow`), SQLite (nativo, módulo `sqlite3`).

## Funcionalidades do sistema

- 8 mesas exibidas em grade (verde = livre, vermelho = ocupada) + atendimento de Balcão / Para Viagem
- Comanda por mesa: lançar itens, ver itens, remover itens, fechar conta
- Pagamento em Dinheiro, Cartão ou PIX
- Cardápio com categorias (Bebida, Tira-Gosto, Lanche, Cigarro) e controle de estoque
- Cadastro de produtos
- Relatórios de caixa (dia, semana, mês)

## Estado atual (antes da reestruturação)

Toda a lógica e os dados ficam em memória dentro do `main.py`. As pastas `models`, `services`, `data` e `templates` estão vazias. As telas ficam em `views/`.

### Bugs conhecidos

1. **ImportError ao fechar conta:** `main.py` importa `escolher_forma_pagamento_view` de `views/tela_pagamento.py`, mas a função lá se chama `escolher_forma_pagamento` e não recebe o callback `confirmar_pagamento`.
2. **`from main import ...` dentro das views** (`tela_pagamento.py`, `tela_principal.py`, `tela_relatorios.py`). Como o programa roda via `python main.py` (módulo `__main__`), isso carrega uma segunda cópia do `main.py`, com dados separados e sem `root_global`. Consequências: vendas registradas numa cópia que os relatórios não enxergam, e `NameError` ao atualizar as mesas.
3. **Comanda não persiste:** em `tela_pedido.py` os itens ficam numa lista local da janela. Fechar a janela perde a comanda. `mesas_status` nunca vira `"ocupada"` e `pedidos_abertos` nunca é preenchido.
4. **Estoque baixa ao clicar em "+"**, não no pagamento. Fechar sem pagar baixa estoque sem registrar venda.
5. **Pagamento de balcão** remove sempre o último pedido aberto, não o que está sendo pago.
6. **Venda não guarda os itens**, só total, forma de pagamento e tipo.
7. **Relatório:** "Vendas registradas" mostra o total geral, não do período. `views/tela_relatorios.py` existe mas não é usado (o relatório está montado dentro do `main.py`).
8. **`tela_principal.py`:** botão "Sobre" é criado dentro do loop das mesas (8 vezes); caminho da logo é absoluto (`C:\tucandeira-bar\assets\logo.png`); código de desenhar mesas duplicado em `criar_tela_principal` e `atualizar_tela_mesas`.
9. **Tela de pedido:** total exibido como `28.0` em vez de `R$ 28,00`; texto de estoque não atualiza; layout do canvas (`side="left"`, `expand=True`) pode esconder o total e o botão "Fechar Conta".
10. **Cadastro:** só adiciona produto; não edita, não exclui, não valida nome duplicado nem preço negativo.
11. Constantes de cor repetidas em todos os arquivos.

## Arquitetura alvo

```
tucandeira-bar/
├── main.py              # só inicializa o banco e abre a tela principal
├── config.py            # cores, fontes, NUM_MESAS, caminhos (pathlib, relativo ao projeto)
├── database.py          # conexão SQLite, criação das tabelas, carga inicial do cardápio
├── models/              # dataclasses: Usuario, Produto, Categoria, Comanda, ItemComanda, Venda, ItemVenda, Pagamento, Caixa...
├── services/            # regras de negócio, SEM nenhum import de tkinter
│   ├── usuarios.py
│   ├── produtos.py
│   ├── caixa.py
│   ├── comandas.py
│   ├── pagamentos.py
│   ├── relatorios.py
│   └── backup.py
├── views/               # só interface; chama services, nunca acessa o banco direto
├── data/tucandeira.db   # banco (não versionar)
├── assets/logo.png
└── tests/               # pytest para os services
```

### Regras de arquitetura

- **Views nunca fazem `from main import`.** Recebem o que precisam por parâmetro ou chamam os services.
- **Services não usam `messagebox` nem nada de Tkinter.** Em caso de erro, lançam exceção (ex.: `CaixaFechadoError`, `PermissaoNegadaError`) e a view decide como mostrar.
- Caminhos de arquivo sempre com `pathlib.Path(__file__).resolve().parent`.
- Valores monetários exibidos no formato `R$ 1.234,56`. Criar uma função `formatar_moeda()` em um único lugar.
- Datas gravadas no banco em ISO (`YYYY-MM-DD HH:MM:SS`).
- O estado das mesas vem do banco: mesa ocupada = existe comanda aberta para ela; "conta pedida" é um status da comanda.

## Regras de trabalho

- Trabalhar **uma etapa por vez** conforme o `ROTEIRO.md`. Ao terminar uma etapa, rodar o sistema/testes, resumir o que mudou e aguardar confirmação antes da próxima.
- Fazer commit no git ao fim de cada etapa, com mensagem em português.
- Perguntar antes de apagar arquivos ou mudar o comportamento de alguma funcionalidade existente.
- Nunca apagar nem recriar o arquivo `data/tucandeira.db` com dados reais; alterações de estrutura devem preservar os dados.
- Manter o visual atual (fundo verde `#004d26`, botões pretos, destaque amarelo `#ffcc00`, fonte Impact nos títulos).

## Decisões tomadas

- **Produto sem estoque:** avisar e permitir a venda. O estoque pode ficar negativo, e isso aparece destacado nos relatórios.
- **Taxa de serviço de 10%:** ativada por padrão nas mesas, desativada no balcão. Pode ser removida no pagamento (exige PIN de gerente).
- **Pagamento dividido:** uma conta pode ser paga com formas diferentes (ex.: parte PIX, parte dinheiro).
- **Número de mesas:** configurável no `config.py` (`NUM_MESAS`), padrão 8.
- **Remover x cancelar item:** o operador pode remover um item sem PIN até 2 minutos depois de lançá-lo (prazo configurável no `config.py`). Depois disso, só por cancelamento, que exige motivo e PIN de gerente e fica registrado.

## Requisitos do sistema

### Versão 2.0

- **Usuários:** login por PIN de 4 dígitos; perfis Operador e Gerente. Ações que exigem PIN de gerente: cancelar item, dar desconto, remover taxa de serviço, sangria, fechar caixa, cadastrar usuários. Toda operação registra quem fez e quando.
- **Caixa:** o sistema só permite vendas com caixa aberto. Abertura com valor inicial (fundo de troco). Sangria e suprimento com motivo. Fechamento com conferência: valor esperado x valor contado por forma de pagamento, mostrando a diferença.
- **Mesas:** status livre, ocupada e "conta pedida" (cores diferentes); número de pessoas na mesa; transferir comanda para outra mesa; juntar mesas.
- **Comandas:** balcão com várias comandas abertas, identificadas pelo nome do cliente; adicionar e remover itens; observação por item; cancelamento de item já lançado exige motivo e PIN de gerente e fica registrado.
- **Pagamento:** taxa de 10% (regra acima); couvert artístico opcional por pessoa, com valor configurável e ativado no dia de show; desconto em R$ ou % com motivo; dividir entre formas de pagamento; mostrar o valor dividido igualmente por pessoa; cálculo de troco em dinheiro.
- **Produtos e estoque:** cadastrar, editar, desativar; categorias editáveis; estoque mínimo por produto, com alerta; entrada de mercadoria registrada.
- **Relatórios:** vendas por período (dia, semana, mês, intervalo personalizado); total por forma de pagamento; produtos mais vendidos; cancelamentos e descontos com responsável e motivo; produtos com estoque negativo ou abaixo do mínimo; histórico de fechamentos de caixa; exportar para CSV.
- **Segurança dos dados:** backup automático do banco ao abrir o sistema, mantendo os 7 últimos.

### Versão 2.1 (futuro — NÃO implementar agora)

- Impressão de comanda e cupom não fiscal em impressora térmica.
- Emissão de NFC-e via serviço terceirizado.
- Vários computadores em rede.
- Cardápio digital por QR Code.
