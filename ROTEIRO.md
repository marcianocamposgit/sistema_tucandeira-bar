# Roteiro para a versão 2.0 do Tucandeira Rock Bar

Cada etapa tem um prompt pronto para colar no Claude Code. Faça uma de cada vez, teste o sistema e só então siga para a próxima. Os requisitos completos estão na seção "Requisitos do sistema" do CLAUDE.md.

**Ordem das etapas (dependências):** correções → banco → usuários → produtos → caixa → comandas → tela de mesas/comanda → pagamento → relatórios → entrega. Usuários vêm antes de tudo porque toda operação registra quem fez. O caixa vem antes das comandas porque só se vende com caixa aberto.

---

## Etapa 0 — Preparação e segurança ✅ concluída

> Leia o CLAUDE.md e todos os arquivos do projeto. Depois: inicialize um repositório git, crie um .gitignore (ignorando `__pycache__/`, `*.pyc` e `data/*.db`), crie um requirements.txt com as dependências, apague as pastas `__pycache__` e faça o primeiro commit com o código original. Me mostre um resumo do que entendeu do projeto antes de alterar qualquer código.

**Teste:** `git log` mostra o commit inicial.

---

## Etapa 1 — Fazer o sistema funcionar de ponta a ponta

> Corrija os bugs 1, 2 e 8 do CLAUDE.md sem reestruturar o projeto ainda: ajuste o nome e a assinatura da função em tela_pagamento.py, elimine todos os `from main import` das views passando funções e dados por parâmetro, tire o botão "Sobre" de dentro do loop, use caminho relativo para a logo e unifique o código que desenha as mesas. Rode o sistema e confirme que é possível lançar um pedido e pagar sem erro.

**Teste:** abrir uma mesa, lançar itens, pagar, ver o valor no relatório do dia.

---

## Etapa 2 — Configuração, banco de dados e backup

> Crie o config.py com cores, fontes, NUM_MESAS (padrão 8), caminhos e valores padrão (taxa de serviço 10%), e substitua as constantes repetidas em todos os arquivos. Crie a função `formatar_moeda()` num único lugar. Crie o database.py com SQLite em data/tucandeira.db, com tabelas para todos os requisitos da versão 2.0 do CLAUDE.md: usuários, categorias, produtos, entradas de estoque, caixas, movimentos de caixa (sangria/suprimento), comandas (com mesa, nome do cliente, nº de pessoas, status, mesas juntas), itens da comanda (com observação), itens cancelados, vendas, itens da venda, pagamentos (vários por venda), descontos e configurações (ex.: valor do couvert e se é dia de show). Todas as tabelas de operação guardam o usuário e a data/hora. Use um controle de versão do esquema (`PRAGMA user_version`) para que mudanças futuras migrem o banco sem perder dados. Na primeira execução, carregue o cardápio atual do main.py e as categorias atuais. Crie os models como dataclasses. Crie também o backup automático ao abrir o sistema (cópia em data/backups, mantendo as 7 últimas). **Mostre o esquema das tabelas antes de implementar.**

**Teste:** o arquivo `data/tucandeira.db` é criado com os 6 produtos e as 4 categorias; abrir o sistema de novo não duplica nada e cria um backup em `data/backups`; com mais de 7 aberturas, só ficam 7 backups.

---

## Etapa 3 — Usuários e login

> Crie services/usuarios.py (sem tkinter): cadastrar usuário (nome, PIN de 4 dígitos, perfil Operador ou Gerente), editar, desativar, autenticar por PIN e uma função para autorizar uma ação com PIN de gerente. Guarde o PIN com hash (hashlib + salt), nunca em texto puro. Não permitir PIN repetido nem desativar o último gerente. Na primeira execução, se não houver usuários, peça para criar o gerente inicial. Crie a tela de login (PIN com teclado numérico na tela), um diálogo reutilizável "PIN do gerente" para as ações protegidas, a tela de cadastro de usuários (só gerente) e um botão "Trocar usuário" na tela principal, mostrando quem está logado. Adicione o pytest ao requirements.txt e escreva testes para o service com banco temporário.

**Teste:** `pytest` passando; criar o gerente inicial, cadastrar um operador, entrar com cada um; um operador não consegue abrir o cadastro de usuários sem o PIN de gerente.

---

## Etapa 4 — Produtos, categorias e estoque

> Crie services/produtos.py: listar, cadastrar, editar e desativar produtos; validar nome duplicado e preço negativo; categorias editáveis (criar, renomear, desativar); estoque mínimo por produto; registrar entrada de mercadoria (quantidade, custo opcional, usuário, data). Baixa de estoque pode deixar o estoque negativo (regra do CLAUDE.md) — o service apenas informa se ficou abaixo do mínimo ou negativo. Transforme a tela de cadastro em um gerenciador: lista de produtos (Treeview) com nome, categoria, preço, estoque e mínimo, com destaque para estoque baixo ou negativo; botões para novo, editar, desativar, entrada de mercadoria e gerenciar categorias. Escreva os testes com pytest.

**Teste:** `pytest` passando; cadastrar, editar e desativar um produto (o desativado some do cardápio); criar uma categoria nova; dar entrada de 10 unidades e conferir o estoque.

---

## Etapa 5 — Controle de caixa

> Crie services/caixa.py: abrir caixa com valor inicial (fundo de troco), sangria e suprimento com motivo (sangria exige PIN de gerente), consultar o caixa aberto e fechar o caixa com conferência: para cada forma de pagamento, valor esperado x valor contado e a diferença (em dinheiro, o esperado = fundo + vendas em dinheiro + suprimentos − sangrias). Fechar caixa exige PIN de gerente. Só pode haver um caixa aberto por vez, e as vendas só são permitidas com caixa aberto (`CaixaFechadoError`). Crie as telas: abrir caixa, sangria/suprimento e fechamento com a conferência. Mostre na tela principal se o caixa está aberto ou fechado. Escreva os testes com pytest, inserindo pagamentos de teste para validar a conferência.

**Teste:** `pytest` passando; abrir o caixa com R$ 100,00, fazer uma sangria e um suprimento, fechar e conferir os valores esperados.

---

## Etapa 6 — Comandas e mesas (regras de negócio)

> Crie services/comandas.py: abrir comanda de mesa (com número de pessoas) ou de balcão (identificada pelo nome do cliente; várias ao mesmo tempo); adicionar item com observação; remover item sem PIN até 2 minutos depois de lançado (prazo em `config.py`); depois disso, só por cancelamento, que exige motivo e PIN de gerente e fica registrado; alterar número de pessoas; marcar "conta pedida"; transferir comanda para outra mesa livre; juntar mesas (as comandas viram uma só e as mesas ficam vinculadas até o pagamento); listar itens, calcular subtotal e listar comandas abertas. Ao adicionar produto sem estoque, avisar e permitir. Exigir caixa aberto. O estado das mesas (livre, ocupada, conta pedida) vem do banco. Escreva os testes com pytest.

**Teste:** `pytest` passando, cobrindo transferência, junção de mesas, remoção dentro e fora do prazo de 2 minutos e cancelamento com e sem PIN de gerente.

---

## Etapa 7 — Tela de mesas e comanda

> Refaça a tela principal e a tela de pedido usando os services. Mesas com cores diferentes para livre, ocupada e conta pedida, mostrando o número de pessoas e o total parcial. Tela da comanda: cardápio à esquerda, comanda à direita com a lista de itens (nome, qtd, observação, subtotal), botões + e − por item, campo de observação, botões "Conta pedida", "Transferir", "Juntar mesas" e "Cancelar item", total formatado em R$ e botão Fechar Conta sempre visível. A comanda é salva no banco a cada item, então fechar a janela não perde nada. No balcão, uma lista das comandas abertas por nome do cliente, com botão para criar uma nova.

**Teste:** lançar itens na Mesa 2, fechar a janela, reabrir e conferir; fechar e reabrir o programa e conferir de novo; transferir a Mesa 2 para a Mesa 5; juntar as Mesas 3 e 4; abrir duas comandas de balcão com nomes diferentes.

---

## Etapa 8 — Pagamento

> Crie services/pagamentos.py e refaça a tela de pagamento. Cálculo da conta: subtotal + taxa de serviço de 10% (ativada por padrão nas mesas, desativada no balcão; removê-la exige PIN de gerente) + couvert artístico por pessoa (quando for dia de show; valor e ativação nas configurações, alterados pelo gerente) − desconto em R$ ou % (com motivo e PIN de gerente). Mostrar os itens, cada parcela da conta e o valor dividido igualmente por pessoa. Permitir dividir o pagamento entre Dinheiro, Cartão e PIX, mostrando quanto falta; em dinheiro, calcular o troco a partir do valor recebido. Só concluir quando o total estiver pago. Ao confirmar: registrar a venda com itens, pagamentos, taxa, couvert, desconto e usuário; baixar o estoque (avisando estoque baixo/negativo); fechar a comanda; liberar as mesas; atualizar a tela principal. Escreva os testes com pytest.

**Teste:** `pytest` passando; pagar uma mesa de 3 pessoas com taxa, couvert e desconto, parte em PIX e parte em dinheiro com troco; conferir o estoque baixado e os valores no fechamento do caixa.

---

## Etapa 9 — Relatórios

> Crie services/relatorios.py e use views/tela_relatorios.py (removendo o relatório de dentro do main.py). Relatórios por período (dia, semana, mês e intervalo personalizado): total vendido, número de vendas, total por forma de pagamento, taxa de serviço e couvert arrecadados, produtos mais vendidos, cancelamentos e descontos (com responsável e motivo), produtos com estoque negativo ou abaixo do mínimo (destacados) e histórico de fechamentos de caixa com as diferenças. Opção de exportar cada relatório para CSV (separador `;` e UTF-8 com BOM para abrir certo no Excel). Escreva os testes com pytest.

**Teste:** `pytest` passando; conferir os números do relatório contra as vendas feitas nos testes das etapas anteriores e abrir um CSV exportado no Excel.

---

## Etapa 10 — Acabamento e entrega

> Revise o projeto inteiro: tratamento de erros, mensagens amigáveis, conferir que nenhuma view acessa o banco direto e nenhum service importa tkinter. Atualize a versão na tela Sobre para 2.0 e gere um executável com PyInstaller com a logo como ícone (o banco e os backups devem ficar numa pasta gravável ao lado do .exe). Atualize o README.md com instruções de instalação e uso.

**Teste:** rodar o .exe em outra pasta ou computador, fazer login, abrir o caixa, vender, fechar o caixa e ver o relatório.

---

## Versão 2.1 (futuro — não fazer agora)

Impressão térmica de comanda e cupom não fiscal, NFC-e via serviço terceirizado, vários computadores em rede e cardápio digital por QR Code. Ver CLAUDE.md.
