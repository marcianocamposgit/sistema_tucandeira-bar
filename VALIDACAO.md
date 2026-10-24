# Validação completa — uma noite de expediente simulada (ensaio em casa)

Roteiro opcional para o **ensaio em casa** (veja o `INSTALACAO_BAR.md`), com o sistema instalado pelo `INSTALAR.bat` num computador de teste, simulando uma noite inteira com dois aparelhos. **Não faz parte da instalação no bar** (decisão de 24/10/2026) e não vai no pacote de entrega: fica só no repositório, junto com o `validacao_cardapio.csv`.

| Aparelho | Quem | Endereço |
|---|---|---|
| PC servidor (caixa) | **Gerente Demo** (PIN 1234) | `http://localhost:5000` |
| Tablet (garçom) | **Ana** (PIN 1111) | o endereço da janela do servidor, ex.: `http://192.168.0.10:5000` |

Os usuários e o cardápio desta noite são só para o ensaio: no fim, o banco inteiro é guardado à parte com o `COMECAR_BANCO_LIMPO.bat` (ou apagado com o `DESINSTALAR.bat` + **APAGAR**).

Siga os passos **na ordem**. Cada **✔ Conferir** traz o valor que deve aparecer na tela. Se algo não bater, anote o número do passo e o que apareceu, e continue se der.

> Este roteiro foi executado pelo cliente de teste do Flask, num banco de produção novo, em 19/10/2026 (preparação com a planilha, a noite inteira e os relatórios): **todos os valores conferiram**. Em 24/10/2026 o passo 0 foi ajustado para o banco novo sem cardápio (a instalação começa zerada).

---

## 0. Preparação

1. O servidor está aberto (janela verde "Tucandeira Rock Bar — Servidor") e o banco está **novo**, sem nenhum usuário. Se já foi usado, rode antes o `COMECAR_BANCO_LIMPO.bat`. O banco novo não tem nenhum produto nem categoria.
2. **PC:** no navegador (`http://localhost:5000`), o sistema pede o primeiro acesso: crie o gerente **Gerente Demo** com PIN **1234**.
3. **PC:** Usuários → cadastrar **Ana**, perfil **Operador**, PIN **1111** (autorize com Gerente Demo, 1234).
4. **PC:** Produtos → **Importar planilha** → envie o arquivo **`validacao_cardapio.csv`** (está na raiz do repositório) → **Conferir planilha**.

   ✔ **Conferir:** Novos **13**, Alterados **0**, Sem mudança **0**, Com erro **0**; categorias novas: **Bebida, Tira-Gosto, Lanche, Cigarro**; nenhum produto para desativar.
5. **Gravar no cardápio** → Gerente Demo, PIN 1234.

   ✔ **Conferir:** mensagem **"Cardápio importado: 13 produtos novos, 4 categorias novas."** e, em Produtos, este estoque:

   | Produto | Estoque |
   |---|---|
   | Brahma Lata | 80 |
   | Heineken Long Neck | 25 |
   | Caipirinha | 13 |
   | Porção Calabresa | 7 |
   | X-Burguer | 4 |
   | Original 600ml | 6 |
   | Misto Quente | 5 |
6. **Tablet:** conectado ao Wi-Fi do bar, abra no Chrome, numa aba comum, o endereço que aparece na janela do servidor e entre como **Ana** (1111). Gire o tablet: retrato e paisagem sem nada cortado.

> A sessão expira após 15 minutos sem uso. Se cair, entre de novo: nada se perde.

---

## 1. Abrir o caixa (PC)

1. Menu → **Caixa** → fundo de troco **100,00** → abrir.

✔ **Conferir** em "Esperado no caixa agora": Dinheiro **R$ 100,00**; Débito, Crédito e PIX **R$ 0,00**.

---

## 2. Abrir as mesas e os balcões (tablet, Ana)

Lance um toque por unidade (4× = tocar 4 vezes no produto). A observação é posta pelo botão **Obs.** do item, na aba Comanda.

| Comanda | Pessoas | Itens | Total |
|---|---|---|---|
| **Mesa 1** | 2 | 4× Brahma Lata, 1× Porção Calabresa (Obs.: **bem passado**) | **R$ 60,00** |
| **Mesa 2** | 3 | 3× Heineken Long Neck, 2× Caipirinha (Obs.: **pouco açúcar**) | **R$ 72,00** |
| **Mesa 3** | 2 | 2× Coca-Cola Lata, 1× Batata Frita, 1× **X-Burguer** | **R$ 59,00** |
| **Mesa 4** | 4 | 4× Brahma Lata | **R$ 32,00** |
| **Balcão — Carla** | — | 1× X-Tudo (Obs.: **sem cebola**), 1× Coca-Cola Lata | **R$ 34,00** |
| **Balcão — Diego** | — | 2× Pastel Carne, 1× Marlboro 20un | **R$ 32,00** |

> Anote a hora em que lançou o **X-Burguer** da Mesa 3: ele vai ser cancelado no passo 4, depois de 2 minutos.

✔ **Conferir no PC**, sem recarregar a página:
- Tela de mesas: Mesas **1, 2, 3 e 4 ocupadas**, as outras livres (atualiza sozinha em até 5 segundos).
- Caixa → "Contas a receber": as 6 comandas com os totais da tabela.
- Abrindo as comandas no PC: as observações **bem passado**, **pouco açúcar** e **sem cebola** aparecem nos itens.

---

## 3. Remover um item antes de 2 minutos (tablet)

1. Mesa 4: lance **1× Original 600ml** por engano.

   ✔ Total da Mesa 4: **R$ 46,00**.
2. Logo em seguida (antes de 2 minutos), toque em **−** no Original 600ml.

✔ **Conferir:** sai **sem pedir PIN**; total da Mesa 4 volta a **R$ 32,00**.

---

## 4. Cancelar um item depois de 2 minutos (tablet, com PIN)

1. Pelo menos 2 minutos depois de lançar o X-Burguer, abra a Mesa 3 e toque em **−** no X-Burguer.

   ✔ Em vez de remover, abre o quadro **Cancelar item**.
2. Motivo **Cliente desistiu** → autorização: **Gerente Demo**, PIN **1234** (digitado no tablet).

✔ **Conferir:** total da Mesa 3 **R$ 37,00**.

---

## 5. Transferir uma mesa e juntar duas (tablet)

1. Mesa 4 → **Transferir** → mesa **6**.
2. Mesa 2 → **Juntar mesas** → **Mesa 3** (ocupada).

✔ **Conferir:**
- A comanda passa a se chamar **Mesas 2 + 3**, com total **R$ 109,00** e **5 pessoas**.
- A antiga Mesa 4 agora é a **Mesa 6**, com total **R$ 32,00**.
- Tela de mesas no PC: **2, 3 e 6 ocupadas**, **4 livre**, 1 continua ocupada.

---

## 6. Conta pedida (tablet)

1. Mesa 1 → **Conta pedida**.

✔ **Conferir no PC:** a Mesa 1 muda para a cor de **conta pedida** em até 5 segundos.

---

## 7. Pagamento parcial em duas formas, com troco (Mesa 1)

1. Tablet: Mesa 1 → **Fechar Conta**.

   ✔ Total **R$ 60,00**; Por pessoa (2 pessoas) **R$ 30,00**.
2. Tablet: **PIX**, botão "1 pessoa R$ 30,00" → Confirmar.

   ✔ No PC, na tela de pagamento da Mesa 1: Já pago **R$ 30,00**, Falta pagar **R$ 30,00**.
3. PC: **Dinheiro**, valor **30,00**, dinheiro recebido **50,00** → Confirmar.

✔ **Conferir:**
- Mensagem **Troco: R$ 20,00** e venda concluída.
- Mesa 1 **livre** nos dois aparelhos.
- Estoque (Produtos): Brahma Lata **76** (80 − 4) e Porção Calabresa **6** (7 − 1). O estoque só baixa no pagamento.

---

## 8. Estorno de pagamento (Balcão — Carla, PC)

1. PC: Carla → Fechar Conta → **Débito 20,00** → Confirmar.
2. Na lista de pagamentos: **Estornar** o débito → motivo **Forma errada** → Gerente Demo, PIN 1234.

   ✔ O débito fica marcado como **(estornado)**; Falta pagar volta a **R$ 34,00**.
3. **Crédito 34,00** → Confirmar.

✔ **Conferir:** venda concluída; Carla some do balcão.

---

## 9. Desconto: ligar, aplicar e desligar (PC)

1. PC: tela de pagamento de **Mesas 2 + 3**.

   ✔ **Não** existe o botão "Dar desconto" (o desconto vem desligado).
2. Menu → **Configurações** → ligar o desconto → Gerente Demo, PIN 1234.
3. Volte ao pagamento de Mesas 2 + 3 → **Dar desconto** → **9,00**, motivo **Demora na cozinha** → PIN 1234.

   ✔ Total **R$ 100,00**; Falta pagar **R$ 100,00**; Por pessoa (5 pessoas) **R$ 20,00**.
4. Menu → **Configurações** → **desligar** o desconto (PIN 1234).

   ✔ No pagamento de Mesas 2 + 3, o botão "Dar desconto" **sumiu**, mas o desconto de R$ 9,00 já lançado **continua** na conta.
5. Tablet: Mesas 2 + 3 → Fechar Conta → **Débito 40,00** (duas pessoas pagaram a parte delas).

✔ **Conferir no PC:** Já pago **R$ 40,00**, Falta pagar **R$ 60,00**.

---

## 10. Suprimento e sangria (PC)

1. Caixa → **+ Suprimento** → **50,00**, motivo **Reforço de troco**.
2. Caixa → **− Sangria** → **30,00**, motivo **Pagamento do gelo** → confirmar com Gerente Demo, PIN 1234.

✔ **Conferir** em "Esperado no caixa agora":

| Dinheiro | Débito | Crédito | PIX |
|---|---|---|---|
| **R$ 150,00** | **R$ 40,00** | **R$ 34,00** | **R$ 30,00** |

O dinheiro é 100 (fundo) + 30 (Mesa 1) + 50 (suprimento) − 30 (sangria). O débito estornado da Carla não conta.

---

## 11. Estoque: entrada, perda e produto desativado

1. PC: Produtos → **Heineken Long Neck** → **Entrada** → **24**, observação **Compra do dia**.

   ✔ Estoque **49** (25 + 24).
2. PC: Produtos → **Brahma Lata** → **Perda** → **1**, motivo **Lata amassada** → PIN 1234.

   ✔ Estoque **75** (76 − 1).
3. Tablet: abra a comanda do **Balcão — Diego**, aba Cardápio, categoria Lanche.

   ✔ **Misto Quente** aparece no cardápio.
4. PC: Produtos → **Misto Quente** → **Desativar** → PIN 1234.

✔ **Conferir no tablet**, sem tocar em nada: em até 5 segundos a tela se recarrega e o **Misto Quente some** do cardápio.

---

## 12. Reiniciar o servidor no meio da noite

1. PC: na janela do servidor, **Parar o servidor** → Sim. Espere uns segundos (o tablet pode mostrar falha de conexão).
2. Abra de novo pelo atalho **Tucandeira Rock Bar** da Área de Trabalho.

   ✔ A janela do servidor mostra o mesmo endereço e "Último backup" com a hora de agora (o backup é feito ao abrir).

✔ **Conferir**, sem fazer login de novo nos dois aparelhos:
- Mesas ocupadas: **2, 3 e 6**.
- Mesas 2 + 3: Total **R$ 100,00**, Já pago **R$ 40,00**, Falta pagar **R$ 60,00**; o desconto de R$ 9,00 continua.
- Mesa 6: **R$ 32,00**. Balcão — Diego: **R$ 32,00**.
- Caixa: Dinheiro **R$ 150,00**, Débito **R$ 40,00**, Crédito **R$ 34,00**, PIX **R$ 30,00**.

---

## 13. Contingência: tablet sem Wi-Fi, só o PC

1. **Desligue o Wi-Fi do tablet.** Daqui em diante, tudo é feito só pelo PC.
2. PC: Balcão — Diego → lance **1× Água sem Gás** → total **R$ 36,00** → **PIX 36,00**.
3. PC: Mesa 6 → lance **+1 Brahma Lata** → total **R$ 40,00** → **Dinheiro 40,00**, recebido **50,00**.

   ✔ **Troco: R$ 10,00**.
4. PC: Mesas 2 + 3 → **Crédito 60,00**.

✔ **Conferir:**
- **Todas as mesas livres** e nenhum balcão aberto.
- Caixa:

  | Dinheiro | Débito | Crédito | PIX |
  |---|---|---|---|
  | **R$ 190,00** | **R$ 40,00** | **R$ 94,00** | **R$ 66,00** |

- Estoque: Brahma Lata **70**, Heineken Long Neck **46**, Caipirinha **11**, X-Burguer **4** (o cancelado não baixa), Original 600ml **6** (o removido não baixa), Misto Quente **5** (desativado).
5. Religue o Wi-Fi do tablet.

   ✔ A tela de mesas volta a atualizar e mostra tudo livre.

---

## 14. Fechar o caixa com uma pequena diferença (PC)

1. Caixa → **Fechar caixa** → valores contados:

   | Dinheiro | Débito | Crédito | PIX |
   |---|---|---|---|
   | **188,00** | **40,00** | **94,00** | **66,00** |

   ✔ Na conferência, Dinheiro: esperado **R$ 190,00**, contado **R$ 188,00**, diferença **-R$ 2,00 faltou**; as outras formas mostram **confere**; Diferença total **-R$ 2,00**.
2. Observação **Faltou troco** → confirmar com Gerente Demo, PIN 1234.

✔ **Conferir:** resumo do fechamento com a mesma conferência, o suprimento de R$ 50,00 e a sangria de R$ 30,00.

---

## 15. Relatórios do dia e CSV (PC)

Menu → **Relatórios** → **Hoje**. O período é a data em que o caixa foi aberto: mesmo que a noite passe da meia-noite, tudo fica no mesmo dia.

✔ **Vendas:** Total vendido **R$ 270,00**; Vendas **5**; Ticket médio **R$ 54,00**; Descontos **R$ 9,00**.

✔ **Por forma de pagamento:**

| Dinheiro | Débito | Crédito | PIX | Total |
|---|---|---|---|---|
| **R$ 70,00** | **R$ 40,00** | **R$ 94,00** | **R$ 66,00** | **R$ 270,00** |

(Dinheiro aqui são só as vendas, 30 + 40, sem fundo, suprimento nem sangria.)

✔ **Produtos mais vendidos**, nesta ordem:

| Produto | Qtd. | Total |
|---|---|---|
| Brahma Lata | 9 | R$ 72,00 |
| Heineken Long Neck | 3 | R$ 36,00 |
| Coca-Cola Lata | 3 | R$ 18,00 |
| Caipirinha | 2 | R$ 36,00 |
| Pastel Carne | 2 | R$ 14,00 |
| Porção Calabresa | 1 | R$ 28,00 |
| X-Tudo | 1 | R$ 28,00 |
| Batata Frita | 1 | R$ 25,00 |
| Marlboro 20un | 1 | R$ 18,00 |
| Água sem Gás | 1 | R$ 4,00 |

O X-Burguer cancelado e o Original 600ml removido **não** aparecem.

✔ **Cancelamentos e estornos** (2 linhas):
- Item cancelado — **R$ 22,00** · **Mesas 2 + 3** · 1× X-Burguer · Cliente desistiu · lançado por **Ana** · autorizado por **Gerente Demo**. Aparece como "Mesas 2 + 3" porque a Mesa 3 foi juntada depois.
- Estorno de pagamento — **R$ 20,00** · **Balcão — Carla** · Pagamento em Débito · Forma errada · Gerente Demo.

✔ **Descontos:** 1 linha, **R$ 9,00** · Mesas 2 + 3 · Demora na cozinha · lançado e autorizado por Gerente Demo.

✔ **Estoque em alerta** (situação de agora): só **Original 600ml** (6, mínimo 12) e **X-Burguer** (4, mínimo 5), **abaixo do mínimo**. O Misto Quente, desativado, não aparece.

✔ **Fechamentos de caixa:** o caixa de hoje com Dinheiro **-R$ 2,00 faltou** e Diferença total **-R$ 2,00**.

### CSV no Excel

1. Em **Vendas**, toque em **Baixar CSV** e abra o arquivo no Excel com dois cliques.

   ✔ Duas colunas (Item / Valor), acentos certos ("Débito", "Período"), **Total vendido (R$) 270,00**, Subtotal **279,00**, Descontos **9,00**, PIX **66,00**.
2. Baixe também o CSV de **Fechamentos de caixa**.

   ✔ Uma linha com Dinheiro esperado **190,00**, contado **188,00**, diferença **-2,00** e Diferença total **-2,00**, cada valor na sua coluna.

---

## Resultado

| Passo | OK? | Observação |
|---|---|---|
| 1. Abrir caixa | | |
| 2. Mesas e balcões | | |
| 3. Remover antes de 2 min | | |
| 4. Cancelar com PIN | | |
| 5. Transferir e juntar | | |
| 6. Conta pedida | | |
| 7. Pagamento parcial e troco | | |
| 8. Estorno | | |
| 9. Desconto | | |
| 10. Suprimento e sangria | | |
| 11. Estoque e produto desativado | | |
| 12. Reiniciar o servidor | | |
| 13. Contingência pelo PC | | |
| 14. Fechar o caixa | | |
| 15. Relatórios e CSV | | |

Para repetir a validação do zero: `COMECAR_BANCO_LIMPO.bat` e volte ao passo 0.

## Depois do ensaio

1. Dois cliques em **`COMECAR_BANCO_LIMPO.bat`** e digite **LIMPAR**: o banco do ensaio vai para `C:\TucandeiraBar\dados\testes_<data e hora>\` e o sistema recomeça vazio.
2. Siga o `INSTALACAO_BAR.md` (fim do ensaio em casa, com o `DESINSTALAR.bat`).
3. Os usuários **Gerente Demo** e **Ana** e os PINs 1234 e 1111 **não** existem mais e nunca devem ser recriados no bar.
