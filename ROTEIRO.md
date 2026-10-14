# Roteiro para finalizar o Tucandeira Rock Bar

Cada etapa tem um prompt pronto para colar no Claude Code. Faça uma de cada vez, teste o sistema e só então siga para a próxima.

---

## Etapa 0 — Preparação e segurança

> Leia o CLAUDE.md e todos os arquivos do projeto. Depois: inicialize um repositório git, crie um .gitignore (ignorando `__pycache__/`, `*.pyc` e `data/*.db`), crie um requirements.txt com as dependências, apague as pastas `__pycache__` e faça o primeiro commit com o código original. Me mostre um resumo do que entendeu do projeto antes de alterar qualquer código.

**Teste:** `git log` mostra o commit inicial.

---

## Etapa 1 — Fazer o sistema funcionar de ponta a ponta

> Corrija os bugs 1, 2 e 8 do CLAUDE.md sem reestruturar o projeto ainda: ajuste o nome e a assinatura da função em tela_pagamento.py, elimine todos os `from main import` das views passando funções e dados por parâmetro, tire o botão "Sobre" de dentro do loop, use caminho relativo para a logo e unifique o código que desenha as mesas. Rode o sistema e confirme que é possível lançar um pedido e pagar sem erro.

**Teste:** abrir uma mesa, lançar itens, pagar, ver o valor no relatório do dia.

---

## Etapa 2 — Configuração e banco de dados

> Crie o config.py com cores, fontes, NUM_MESAS e caminhos, e substitua as constantes repetidas em todos os arquivos. Crie o database.py com SQLite em data/tucandeira.db, com as tabelas: produtos, comandas, itens_comanda, vendas e itens_venda. Na primeira execução, carregue o cardápio atual do main.py como dados iniciais. Crie os models como dataclasses. Mostre o esquema das tabelas antes de implementar.

**Teste:** o arquivo `data/tucandeira.db` é criado e contém os 6 produtos.

---

## Etapa 3 — Services (regras de negócio)

> Crie os services conforme o CLAUDE.md, sem nenhum import de tkinter:
> - produtos: listar, cadastrar, editar, desativar, validar nome duplicado e preço
> - comandas: abrir comanda (mesa ou balcão), adicionar item, remover item, listar itens, calcular total, listar comandas abertas
> - pagamentos: fechar comanda, registrar venda com os itens, baixar estoque no pagamento
> - relatorios: total e quantidade de vendas por período, total por forma de pagamento, produtos mais vendidos
> Escreva testes com pytest para cada service usando um banco temporário.

**Teste:** `pytest` passando.

---

## Etapa 4 — Nova tela de pedido (comanda)

> Refaça a tela de pedido usando os services: cardápio à esquerda, comanda à direita com a lista de itens (nome, qtd, subtotal), botões de + e − por item, total formatado em R$ e botão Fechar Conta sempre visível. A comanda é salva no banco a cada item, então fechar a janela não perde nada. A mesa fica vermelha ao ter comanda aberta e volta a verde após o pagamento. No balcão, permitir várias comandas abertas, cada uma com um nome ou número.

**Teste:** lançar itens na Mesa 2, fechar a janela, reabrir e conferir os itens; fechar e reabrir o programa e conferir de novo.

---

## Etapa 5 — Pagamento

> Refaça a tela de pagamento: mostra os itens e o total, permite escolher Dinheiro, Cartão ou PIX, e em Dinheiro calcula o troco a partir do valor recebido. [Incluir aqui as decisões sobre taxa de 10% e divisão de pagamento.] Ao confirmar, chama o service de pagamento, atualiza as mesas e fecha as janelas.

**Teste:** pagar uma conta em dinheiro com troco e conferir o estoque baixado.

---

## Etapa 6 — Cadastro de produtos

> Transforme a tela de cadastro em um gerenciador: lista de produtos (Treeview) com nome, categoria, preço e estoque; botões para novo, editar, desativar e dar entrada de estoque. Use as validações do service.

**Teste:** cadastrar, editar e desativar um produto; o desativado some do cardápio.

---

## Etapa 7 — Relatórios e fechamento de caixa

> Use views/tela_relatorios.py (removendo o relatório de dentro do main.py). Mostre para dia, semana e mês: total vendido, número de vendas, total por forma de pagamento e produtos mais vendidos. Adicione o fechamento de caixa do dia e a opção de exportar o relatório para CSV.

**Teste:** conferir os números do relatório contra as vendas feitas nos testes.

---

## Etapa 8 — Acabamento e entrega

> Revise o projeto inteiro: tratamento de erros, mensagens amigáveis, backup automático do banco ao abrir o sistema (pasta data/backups, mantendo os 7 últimos), atualize a versão na tela Sobre para 2.0 e gere um executável com PyInstaller com a logo como ícone. Escreva um README.md com instruções de instalação e uso.

**Teste:** rodar o .exe em outra pasta ou computador.
