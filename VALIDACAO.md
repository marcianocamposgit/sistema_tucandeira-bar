# Validação em casa — uma noite completa de expediente

Roteiro para executar **antes das Etapas 9 e 10**, simulando uma noite inteira do bar com dois aparelhos:

| Aparelho | Quem | Endereço |
|---|---|---|
| PC (caixa) | **Gerente Demo** (PIN 1234) | `http://localhost:5000` |
| Celular (garçom) | **Ana** (PIN 1111) | `http://192.168.137.1:5000`, pelo Hotspot móvel do Windows |

Siga os passos **na ordem**. Cada **✔ Conferir** traz o valor que deve aparecer na tela. Se algo não bater, anote o número do passo e o que apareceu, e continue se der.

> Este roteiro foi executado pelo cliente de teste do Flask, num banco temporário copiado do banco de demonstração, em 19/10/2026: **todos os valores conferiram**.

---

## 0. Preparação

1. Banco de demonstração recriado em 19/10/2026 com:
   ```
   python scripts/popular_demo.py --recriar --sem-movimento-hoje
   ```
   Ele tem o histórico das noites anteriores, o **caixa fechado**, nenhuma comanda aberta e o **desconto desligado**.
2. **Estoque no início** (confira em Produtos antes de começar):

   | Produto | Estoque |
   |---|---|
   | Brahma Lata | 80 |
   | Heineken Long Neck | 25 |
   | Caipirinha | 13 |
   | Porção Calabresa | 7 |
   | X-Burguer | 4 |
   | Original 600ml | 6 |
   | Misto Quente | 5 |

   Se o banco for recriado em outro dia, esses números mudam (o histórico é sorteado a partir da data). Nesse caso, anote os do início e faça as contas pelas diferenças indicadas nos passos.
3. No PC: ligue o **Hotspot móvel** (Configurações → Rede e Internet → Hotspot móvel) e conecte o celular nele. O firewall do Windows fica **ligado**.
4. No PC, numa janela de terminal:
   ```
   cd C:\tucandeira-bar
   python servidor.py
   ```
5. PC: abra `http://localhost:5000` e entre como **Gerente Demo** (1234).
6. Celular: abra `http://192.168.137.1:5000` numa aba comum do Chrome e entre como **Ana** (1111).

> A sessão expira após 15 minutos sem uso. Se cair, entre de novo: nada se perde.

---

## 1. Abrir o caixa (PC)

1. Menu → **Caixa** → fundo de troco **100,00** → abrir.

✔ **Conferir** em "Esperado no caixa agora": Dinheiro **R$ 100,00**; Débito, Crédito e PIX **R$ 0,00**.

---

## 2. Abrir as mesas e os balcões (celular, Ana)

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

## 3. Remover um item antes de 2 minutos (celular)

1. Mesa 4: lance **1× Original 600ml** por engano.

   ✔ Total da Mesa 4: **R$ 46,00**.
2. Logo em seguida (antes de 2 minutos), toque em **−** no Original 600ml.

✔ **Conferir:** sai **sem pedir PIN**; total da Mesa 4 volta a **R$ 32,00**.

---

## 4. Cancelar um item depois de 2 minutos (celular, com PIN)

1. Pelo menos 2 minutos depois de lançar o X-Burguer, abra a Mesa 3 e toque em **−** no X-Burguer.

   ✔ Em vez de remover, abre o quadro **Cancelar item**.
2. Motivo **Cliente desistiu** → autorização: **Gerente Demo**, PIN **1234** (digitado no celular).

✔ **Conferir:** total da Mesa 3 **R$ 37,00**.

---

## 5. Transferir uma mesa e juntar duas (celular)

1. Mesa 4 → **Transferir** → mesa **6**.
2. Mesa 2 → **Juntar mesas** → **Mesa 3** (ocupada).

✔ **Conferir:**
- A comanda passa a se chamar **Mesas 2 + 3**, com total **R$ 109,00** e **5 pessoas**.
- A antiga Mesa 4 agora é a **Mesa 6**, com total **R$ 32,00**.
- Tela de mesas no PC: **2, 3 e 6 ocupadas**, **4 livre**, 1 continua ocupada.

---

## 6. Conta pedida (celular)

1. Mesa 1 → **Conta pedida**.

✔ **Conferir no PC:** a Mesa 1 muda para a cor de **conta pedida** em até 5 segundos.

---

## 7. Pagamento parcial em duas formas, com troco (Mesa 1)

1. Celular: Mesa 1 → **Fechar Conta**.

   ✔ Total **R$ 60,00**; Por pessoa (2 pessoas) **R$ 30,00**.
2. Celular: **PIX**, botão "1 pessoa R$ 30,00" → Confirmar.

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
5. Celular: Mesas 2 + 3 → Fechar Conta → **Débito 40,00** (duas pessoas pagaram a parte delas).

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
3. Celular: abra a comanda do **Balcão — Diego**, aba Cardápio, categoria Lanche.

   ✔ **Misto Quente** aparece no cardápio.
4. PC: Produtos → **Misto Quente** → **Desativar** → PIN 1234.

✔ **Conferir no celular**, sem tocar em nada: em até 5 segundos a tela se recarrega e o **Misto Quente some** do cardápio.

---

## 12. Reiniciar o servidor no meio da noite

1. PC: na janela do servidor, **Ctrl+C**. Espere uns segundos (o celular pode mostrar falha de conexão).
2. `python servidor.py` de novo.

✔ **Conferir**, sem fazer login de novo nos dois aparelhos:
- Mesas ocupadas: **2, 3 e 6**.
- Mesas 2 + 3: Total **R$ 100,00**, Já pago **R$ 40,00**, Falta pagar **R$ 60,00**; o desconto de R$ 9,00 continua.
- Mesa 6: **R$ 32,00**. Balcão — Diego: **R$ 32,00**.
- Caixa: Dinheiro **R$ 150,00**, Débito **R$ 40,00**, Crédito **R$ 34,00**, PIX **R$ 30,00**.

---

## 13. Contingência: celular sem Wi-Fi, só o PC

1. **Desligue o Wi-Fi do celular.** Daqui em diante, tudo é feito só pelo PC.
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
5. Religue o Wi-Fi do celular.

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

✔ **Estoque em alerta** (situação de agora): Lucky Strike 20un (-4) e Mandioca Frita (-2) com **estoque negativo**; Gin Tônica e Isqueiro **sem estoque**; Isca de Peixe, Original 600ml, Whisky 50ml e X-Burguer **abaixo do mínimo**. O Misto Quente, desativado, não aparece.

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

Para repetir a validação do zero: `python scripts/popular_demo.py --recriar --sem-movimento-hoje` (guarda um backup do banco anterior).
