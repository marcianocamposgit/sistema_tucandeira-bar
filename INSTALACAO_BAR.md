# Instalação no bar — Tucandeira Rock Bar 2.0

Guia prático em três partes: **ensaio em casa** (no notebook), **instalação no bar** e **treinamento rápido** da equipe. Os detalhes de rede, backup e solução de problemas estão no `README.md`.

**A instalação começa 100% zerada:** sem usuários, sem vendas e sem nenhum produto ou categoria. O primeiro acesso cria o gerente, e o cardápio entra só pela importação da planilha do dono (`modelo_cardapio.csv`, que vem só com o cabeçalho).

---

## 1. Ensaio em casa (notebook)

Objetivo: passar uma vez por todo o ciclo — instalar, usar e remover — antes de ir ao bar. Use a mesma pasta `TucandeiraBar-2.0` que vai para o bar.

1. **Extraia** o `TucandeiraBar-2.0.zip` (botão direito → Extrair tudo).
2. **Instale:** dois cliques em `INSTALAR.bat` → aceite o pedido de administrador. Se aparecer o SmartScreen, **Mais informações → Executar assim mesmo**; no aviso do firewall, marque **Redes privadas → Permitir acesso**.
   - ✔ Abre a janela verde do servidor com o endereço; aparece o atalho **Tucandeira Rock Bar** na Área de Trabalho.
3. **Primeiro acesso:** no navegador (`http://localhost:5000`), o sistema pede o gerente. Crie um gerente de teste (ex.: **Teste**, PIN **1234**).
   - ✔ Produtos está vazio: nenhuma categoria, nenhum produto.
4. **Importe uma planilha de teste:** abra o `modelo_cardapio.csv` no Excel, preencha 3 ou 4 linhas inventadas (ex.: `Bebida;Cerveja Teste;8,00;20;5`), salve como **CSV (separado por vírgulas)** e envie em Produtos → **Importar planilha** → **Conferir planilha** → **Gravar no cardápio** (PIN do gerente).
   - ✔ A conferência mostra os produtos como **novos** e as categorias como **novas**; depois de gravar, eles aparecem em Produtos.
5. **Uma venda simples:** Caixa → abrir com fundo de troco **50,00** → Mesas → Mesa 1 → lance 2 itens → **Fechar Conta** → pague em Dinheiro → Caixa → **Fechar caixa** (conte os valores e confirme com o PIN).
   - ✔ A Mesa 1 volta a ficar livre e o relatório de Hoje mostra a venda.
   - Se tiver um celular ou tablet à mão, abra também o endereço da janela do servidor nele (mesmo Wi-Fi) para ver a tela de mesas se atualizando.
6. **Banco limpo:** dois cliques em `COMECAR_BANCO_LIMPO.bat` → digite **LIMPAR**.
   - ✔ O banco do ensaio vai para `C:\TucandeiraBar\dados\testes_<data e hora>\` e o sistema volta a pedir o primeiro acesso, sem produtos.
7. **Desinstale tudo:** dois cliques em `DESINSTALAR.bat` → digite **SIM** → no fim, digite **APAGAR** para apagar também os dados do ensaio.
   - ✔ Somem o atalho, o início automático, a regra do firewall e a pasta `C:\TucandeiraBar\`.

> Quer um teste mais completo? O `VALIDACAO.md` do repositório simula uma noite inteira com valores conferidos (opcional, não faz parte da instalação no bar).

---

## 2. O que levar ao bar

- [ ] Pen drive com a pasta **`TucandeiraBar-2.0`** (ou o `.zip`).
- [ ] **Planilha do cardápio** preenchida pelo dono (`modelo_cardapio.csv` salvo como CSV), de preferência já conferida: categoria, nome, preço, estoque atual e estoque mínimo de cada produto.
- [ ] **Lista dos garçons** (nomes) — cada um escolhe o próprio PIN na hora.
- [ ] O **dono/gerente presente**, para criar o PIN de gerente (só ele deve saber).
- [ ] **Tablet** carregado + carregador.
- [ ] **Cabo de rede** para ligar o computador servidor ao roteador (melhor que Wi-Fi).
- [ ] **Usuário e senha do roteador** (para a reserva de IP; geralmente na etiqueta embaixo dele).
- [ ] Valor do **fundo de troco** para abrir o primeiro caixa.
- [ ] Este guia impresso ou no celular.

---

## 3. Instalação no bar

1. **Copie** a pasta `TucandeiraBar-2.0` para o computador do bar (ex.: Área de Trabalho).
2. **Instale:** dois cliques em `INSTALAR.bat` → aceite o administrador (SmartScreen: **Mais informações → Executar assim mesmo**). No aviso do firewall: **Redes privadas → Permitir acesso** (nunca Cancelar).
3. **Rede privada:** o instalador lista as redes do computador. A rede do bar precisa estar como **Private**; se estiver Public, mude em Configurações → Rede e Internet → propriedades da rede → **Rede privada**.
4. **IP fixo no roteador:** anote o endereço físico e o IPv4 com `ipconfig /all`, faça a **reserva de DHCP** no roteador (README → "Rede do bar → 1. IP fixo") e **reinicie o computador**.
   - ✔ A janela do servidor abre sozinha depois do logon e mostra o IP reservado (ex.: `http://192.168.0.10:5000`).
5. **Teste no tablet:** conecte o tablet ao Wi-Fi principal do bar (não o de visitantes), abra o Chrome e digite o endereço da janela do servidor.
   - ✔ Abre a tela do sistema. Gire o tablet: retrato e paisagem sem nada cortado.
   - Se não abrir: README → "Solução de problemas" (firewall, rede privada, isolamento de clientes no roteador). Enquanto isso, o bar funciona pelo PC.
   - Opcional: app em tela cheia (README → "Abrir como aplicativo").
6. **Gerente real:** no PC (`http://localhost:5000`), o dono cria o usuário **gerente** com o PIN dele.
7. **Cardápio do dono:** Produtos → **Importar planilha** → envie a planilha → **Conferir planilha**. Confira com o dono as linhas, os preços e as categorias novas; corrija no Excel e reenvie se houver linha com erro. Depois **Gravar no cardápio** (PIN do gerente).
8. **Garçons:** Usuários → cadastre cada garçom como **Operador**; cada um digita o próprio PIN de 4 dígitos (autorizado com o PIN do gerente).
9. **Abrir o caixa:** Caixa → informe o fundo de troco → **Abrir caixa**.
   - ✔ O selo **Caixa aberto** aparece no topo, no PC e no tablet.
10. **Conferência final:** tela **Sobre e backup** → **Fazer backup agora** e confira a data do último backup. Pronto para vender.

> Se alguém fizer testes no computador do bar antes da primeira venda real (ex.: uma venda de teste), rode o `COMECAR_BANCO_LIMPO.bat` e refaça os passos 6 a 9. Se a primeira coisa feita for o gerente real e o cardápio do dono, não é preciso.

---

## 4. Treinamento rápido

### Garçons (10 minutos, no tablet)

1. **Entrar:** toque no seu nome e digite o PIN. A sessão sai sozinha depois de 15 minutos parada; é só entrar de novo, nada se perde. Ao passar o tablet para outro garçom, use **Trocar usuário**.
2. **Abrir mesa:** toque numa mesa livre, informe o número de pessoas. Cores: livre, ocupada e conta pedida.
3. **Lançar:** escolha a categoria e toque no produto — **cada toque é 1 unidade**, gravada na hora. Observação ("sem gelo") pelo botão **Obs.** do item, na aba Comanda.
4. **Errou?** O **−** tira o item sem PIN até 2 minutos depois de lançar. Depois disso, só o gerente cancela (com motivo).
5. **Balcão / Para Viagem:** comanda pelo nome do cliente (dois clientes com o mesmo nome: "João 2").
6. **Conta:** toque em **Conta pedida** quando o cliente pedir; a mesa muda de cor para o caixa ver. Se o tablet falhar, avise o caixa: tudo pode ser feito pelo PC.

### Gerente / caixa (20 minutos, no PC)

1. **Caixa:** abrir com o fundo de troco; **+ Suprimento** e **− Sangria** com motivo (sangria pede o PIN do gerente).
2. **Receber:** comanda → **Fechar Conta** → forma de pagamento (Dinheiro, Débito, Crédito, PIX) → valor. Dá para dividir em várias formas e receber aos poucos (cada um paga a sua parte); a tela mostra o já pago, o que falta, o valor por pessoa e o troco.
3. **Ações com PIN de gerente:** cancelar item ou comanda com itens, estornar pagamento, desconto (só se ligado em Configurações), perda e ajuste de estoque, cadastrar usuários. O PIN é pedido na hora, mesmo com o gerente logado.
4. **Cardápio e estoque:** para mudar preços ou incluir produtos, **Baixar modelo** em Importar planilha, editar no Excel e importar de novo; entrada de mercadoria pela tela do produto. O alerta de estoque aparece na tela de mesas.
5. **Fechar o caixa:** só com todas as comandas pagas ou canceladas (o sistema mostra quais faltam). Conte dinheiro, débito, crédito e PIX, confira as diferenças e confirme com o PIN.
6. **Relatórios e backup:** Relatórios → Hoje/semana/mês, com exportação CSV. Backup automático ao abrir e uma vez por dia; de vez em quando, copie `C:\TucandeiraBar\dados\backups\` para um pen drive.
7. **Não fechar** a janela verde do servidor (pode minimizar). Se o computador reiniciar, o servidor abre sozinho no logon.
