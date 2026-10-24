# Tucandeira Rock Bar — Sistema de Gestão para Bares

Sistema web para gestão de bar: mesas, comandas, pagamentos, estoque, controle de caixa e relatórios. Feito em Python com Flask e banco de dados SQLite, funciona só na rede local do bar, sem precisar de internet.

## Como o bar usa o sistema

- **PC servidor (caixa):** um computador com Windows roda o sistema e é usado no caixa, com mouse e teclado, em `http://localhost:5000`.
- **Tablet Android do garçom:** um tablet Android antigo, reaproveitado, abre o sistema pelo Chrome no Wi-Fi do bar para lançar pedidos nas mesas.
- **Celulares Android (opcional, futuro):** os garçons poderão usar o próprio celular da mesma forma. O layout já funciona a partir de 360 px de largura.
- **Plano B:** se o tablet não conectar, o bar inteiro é operado pelo PC, sem Wi-Fi e sem internet (veja "Solução de problemas").

## Status

Versão 2.0 (web) pronta para instalação no bar. O ensaio em casa, a instalação e o treinamento da equipe estão no `INSTALACAO_BAR.md`; o histórico das etapas está no `ROTEIRO.md`.

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
- ✅ Etapa 7 — Produtos e estoque
- ✅ Etapa 8 — Relatórios
- ✅ Etapa 9 — Acesso pela rede, PWA e teste em tablet real (teste no tablet do bar na instalação)
- ✅ Etapa 10 — Backup automático, executável, início com o Windows, importação do cardápio e entrega

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
- **Cardápio por planilha:** o dono preenche no Excel uma planilha (categoria, produto, preço, estoque e estoque mínimo) e o gerente importa pela tela de produtos, vendo antes, linha a linha, o que muda e quais linhas têm erro.
- **Relatórios:** vendas por dia, semana, mês ou intervalo, total por forma de pagamento, produtos mais vendidos, cancelamentos e descontos, estoque negativo ou abaixo do mínimo, histórico de fechamentos de caixa e exportação para CSV. "Hoje" é a noite do caixa: o que acontece depois da meia-noite conta no dia em que o caixa foi aberto.
- **Segurança dos dados:** backup automático do banco ao abrir o servidor e uma vez por dia, mantendo os 7 últimos, e o botão "Fazer backup agora" para o gerente (tela Sobre).
- **Servidor fácil de operar:** um programa só (`TucandeiraBar.exe`), que abre junto com o Windows numa janela que mostra o endereço para o tablet e que não trava com um clique.

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
- Tkinter (janela do servidor, já vem com o Python)
- Pillow (geração dos ícones do PWA e do executável)
- PyInstaller (gera o `TucandeiraBar.exe`, que roda sem Python)
- Fonte Anton (licença OFL), incluída em `static/fonts/`
- pytest (testes)

## Requisitos

- **Computador servidor:** Windows 10 ou superior, conectado à rede do bar (de preferência por cabo) e com IP fixo. **Não precisa de Python**: o sistema é o `TucandeiraBar.exe`.
- **Navegador do PC servidor:** Chrome ou Edge atualizado.
- **Tablet e celulares:** Android com o navegador **Chrome**, inclusive versões antigas (o sistema foi escrito para funcionar em tablets reaproveitados). Celulares com tela a partir de 360 px de largura. Safari, iPhone e iPad não são suportados.
- Os aparelhos precisam estar no mesmo Wi-Fi do computador servidor.
- Não precisa de internet para funcionar — só da rede local.

## Instalação no bar

A instalação começa **100% zerada**: sem usuários, sem vendas e sem nenhum produto ou categoria. O primeiro acesso cria o gerente, e o cardápio entra só pela importação da planilha do dono. O passo a passo detalhado (ensaio em casa, instalação, lista do que levar e treinamento da equipe) está no **`INSTALACAO_BAR.md`**; abaixo, o resumo.

### O que levar

Um pen drive com a pasta **`TucandeiraBar-2.0`** (ou o arquivo `TucandeiraBar-2.0.zip`, gerado por `scripts\gerar_exe.ps1`):

| Arquivo | Para que serve |
|---|---|
| `TucandeiraBar.exe` | o sistema (servidor), roda sem Python |
| `INSTALAR.bat` | instala tudo no computador do bar |
| `ATUALIZAR.bat` | troca o programa por uma versão nova, sem mexer nos dados |
| `COMECAR_BANCO_LIMPO.bat` | opcional: guarda o banco de testes feitos antes da primeira venda e começa do zero |
| `DESINSTALAR.bat` | remove o programa do computador (os dados ficam) |
| `*.ps1` | usados pelos `.bat` (firewall, início com o Windows...) |
| `modelo_cardapio.csv` | planilha do cardápio (só o cabeçalho) para o dono preencher no Excel |
| `README.md` | estas instruções |
| `INSTALACAO_BAR.md` | ensaio em casa, instalação no bar, o que levar e treinamento da equipe |

Leve também o tablet carregado, a planilha do cardápio preenchida pelo dono e, se possível, um cabo de rede para o computador servidor (lista completa no `INSTALACAO_BAR.md`).

### Passo a passo

1. **Copie** a pasta `TucandeiraBar-2.0` para o computador do bar (ex.: na Área de Trabalho). Se veio o `.zip`, clique com o botão direito → Extrair tudo.
2. **Instale:** dois cliques em `INSTALAR.bat` e aceite o pedido de administrador. O instalador:
   - cria `C:\TucandeiraBar\programa\` (o `TucandeiraBar.exe`) e `C:\TucandeiraBar\dados\` (banco, backups, logs);
   - libera a porta 5000 no Firewall do Windows, **só na rede Privada**;
   - faz o servidor abrir sozinho quando o usuário entra no Windows;
   - cria o atalho **Tucandeira Rock Bar** na Área de Trabalho e abre o servidor.

   Se o Windows mostrar "O Windows protegeu o computador" (SmartScreen), clique em **Mais informações → Executar assim mesmo**: o programa não tem assinatura digital paga.
3. **Aviso do firewall:** se aparecer a pergunta do Firewall do Windows sobre o TucandeiraBar, marque **Redes privadas** e clique em **Permitir acesso** (nunca em Cancelar — isso cria um bloqueio; veja "Solução de problemas").
4. **Rede privada:** o instalador mostra as redes do computador. A rede do bar precisa aparecer como **Private**; se estiver Public, mude em Configurações → Rede e Internet → propriedades da rede → **Rede privada**.
5. **IP fixo pelo roteador:** siga "Rede do bar → 1. IP fixo" (reserva de DHCP). Depois, reinicie o computador e confira que a janela do servidor abriu sozinha e mostra o IP reservado.
6. **Teste no tablet:**
   1. Conecte o tablet ao Wi-Fi do bar (a rede principal, não a de visitantes).
   2. No Chrome do tablet, digite o endereço que aparece na janela do servidor (ex.: `http://192.168.0.10:5000`). Deve abrir a tela do sistema.
   3. Se não abrir, siga "Solução de problemas" (firewall, rede privada, isolamento de clientes no roteador). Enquanto isso, o bar funciona só pelo PC.
   4. Opcional: instale como app em tela cheia (veja "Abrir como aplicativo").
7. **Primeiro acesso:** no navegador do computador (`http://localhost:5000`), crie o usuário **gerente** com um PIN que só o dono saiba.
8. **Cardápio do bar:** em Produtos → **Importar planilha**, envie o `modelo_cardapio.csv` preenchido pelo dono no Excel (ou baixe o modelo pela tela), confira linha a linha e grave com o PIN do gerente. As categorias da planilha são criadas na importação.
9. **Garçons:** em Usuários, cadastre cada garçom com o seu PIN (autorizando com o PIN do gerente).
10. Pronto: abra o caixa e comece a vender.

### Começar com o banco limpo (opcional)

Só é preciso se alguém fizer **testes no computador do bar antes da primeira venda real** (ex.: uma venda de teste com usuários ou produtos que não vão ficar). Se a primeira coisa feita depois de instalar for o gerente de verdade e o cardápio do dono, pule esta parte.

1. Dois cliques em `COMECAR_BANCO_LIMPO.bat` e digite **LIMPAR**.
2. O script fecha o servidor e **guarda** (não apaga) o banco, os backups e os logs dos testes em `C:\TucandeiraBar\dados\testes_<data e hora>\`. Depois abre o servidor de novo.
3. O sistema começa vazio (sem usuários, vendas, produtos nem categorias): siga os passos 7 a 10 acima.

Use **só antes da primeira venda real**. Nunca copie o banco do computador de desenvolvimento para o bar e nunca use os dados de demonstração (`popular_demo.py`) no bar.

### Atualizar o sistema

1. Gere a versão nova (`scripts\gerar_exe.ps1`) e leve a pasta `TucandeiraBar-<versão>` ao bar.
2. Com o bar sem movimento (de preferência com o caixa fechado), dois cliques em `ATUALIZAR.bat`.
3. O script fecha o servidor, guarda o programa antigo como `TucandeiraBar.anterior.exe`, coloca o novo em `C:\TucandeiraBar\programa\` e abre de novo. **Os dados não são tocados.** Ao abrir, a versão nova faz um backup e atualiza a estrutura do banco sozinha.
4. Confira: na tela **Sobre**, a versão nova e o último backup (de agora); abra uma mesa de teste e cancele.
5. Se algo der errado: feche o servidor, apague o `TucandeiraBar.exe` novo, renomeie `TucandeiraBar.anterior.exe` para `TucandeiraBar.exe` e restaure o backup feito na atualização (veja "Backup e restauração").

### Desinstalar

Dois cliques em `DESINSTALAR.bat` (pede administrador) e digite **SIM**. Ele fecha o servidor e remove o início automático com o Windows, a regra do firewall, o atalho da Área de Trabalho e a pasta `C:\TucandeiraBar\programa\`. A pasta **`C:\TucandeiraBar\dados\`** (vendas, caixas, usuários, backups) **fica guardada**: no fim, o script explica o que há nela e só a apaga se for digitado **APAGAR**; qualquer outra resposta mantém os dados. Para reinstalar depois, basta o `INSTALAR.bat`: o programa volta a usar os mesmos dados.

### A janela do servidor

O servidor abre numa janela verde com o endereço para os tablets, o último backup e os botões **Abrir o sistema neste computador** e **Parar o servidor**. Ela pode ser minimizada, mas não fechada: fechar a janela para o sistema no caixa e nos tablets (ela pergunta antes). Diferente de uma janela preta de console, clicar nela nunca pausa o servidor. Se o servidor já estiver aberto, os dois cliques no atalho só abrem o sistema no navegador.

## Backup e restauração

- **Automático:** ao abrir o servidor e uma vez por dia enquanto ele estiver aberto, em `C:\TucandeiraBar\dados\backups\` (arquivos `tucandeira_AAAA-MM-DD_HH-MM-SS.db`). Ficam os 7 mais recentes.
- **Na hora:** tela **Sobre e backup** (botão no rodapé do menu) → **Fazer backup agora** (só gerente). A tela mostra a data do último backup.
- **Cópia fora do computador:** de vez em quando, copie a pasta `backups` para um pen drive; se o computador quebrar, os dados estão lá.

**Restaurar um backup** (ex.: o banco estragou, ou uma atualização deu errado):

1. Feche o servidor (botão **Parar o servidor** na janela).
2. Em `C:\TucandeiraBar\dados\`, renomeie `tucandeira.db` para `tucandeira_estragado.db` (se existir) e apague `tucandeira.db-wal` e `tucandeira.db-shm` (se existirem).
3. Copie o backup escolhido de `backups\` para `C:\TucandeiraBar\dados\` e renomeie a cópia para `tucandeira.db`.
4. Abra o servidor (atalho da Área de Trabalho). Tudo o que foi lançado depois daquele backup se perde; confira o caixa.

## Rede do bar

O computador servidor e os tablets precisam estar na **mesma rede** (Wi-Fi do bar ou cabo no mesmo roteador). Três ajustes, feitos uma vez só:

### 1. IP fixo para o computador servidor

Os tablets acessam o servidor pelo IP (ex.: `http://192.168.0.10:5000`). Se o IP mudar, os tablets deixam de encontrar o sistema e a liberação do Chrome (veja "Abrir como aplicativo") precisa ser refeita. Por isso o IP do servidor precisa ser fixo.

**Primeira opção: reserva de DHCP no roteador.** É a mais segura, porque o roteador nunca entrega esse IP para outro aparelho.

1. No computador servidor, abra o Prompt de Comando e digite `ipconfig /all`. Na placa usada (Wi-Fi ou Ethernet), anote o **Endereço Físico** (ex.: `3C-52-82-AA-BB-CC`) e o **Endereço IPv4** (ex.: `192.168.0.10`).
2. Entre na página do roteador (normalmente `http://192.168.0.1` ou `http://192.168.1.1`; usuário e senha ficam na etiqueta embaixo dele).
3. Procure **DHCP** → **Reserva de endereço**, "Address Reservation", "IP estático" ou "DHCP estático". Adicione o endereço físico anotado com o IP desejado e salve.
4. Reinicie o computador servidor e confira com `ipconfig` que o IP é o reservado.

**Segunda opção: IP fixo no Windows** (se o roteador não tiver reserva):

1. Configurações → Rede e Internet → (Wi-Fi ou Ethernet) → a rede conectada → **Atribuição de IP** → Editar → **Manual** → IPv4 ligado.
2. Preencha o IP (ex.: `192.168.0.10`, fora da faixa que o roteador distribui, se souber qual é), a máscara `255.255.255.0`, o gateway (IP do roteador, ex.: `192.168.0.1`) e o DNS (o próprio IP do roteador).
3. Salve e confira que `http://localhost:5000` e a internet continuam funcionando.

### 2. Liberar a porta no Firewall do Windows (só rede privada)

O `INSTALAR.bat` já faz isso. O script `liberar_firewall.ps1` cria **uma** regra de entrada, só para a porta do sistema (5000) e só no perfil de rede **Privada**. Redes públicas continuam bloqueadas. Para rodar à mão (ex.: depois de mudar a porta):

1. Abra o **PowerShell como administrador** (menu Iniciar → digite PowerShell → botão direito → Executar como administrador).
2. Vá até a pasta do script e rode:
   ```
   powershell -ExecutionPolicy Bypass -File .\liberar_firewall.ps1
   ```
   (Se mudou a porta no `config.py`: `-Porta 5001`. Para remover a regra: `-Desfazer`.)
3. O script mostra as redes do computador. A rede do bar precisa estar como **Private**. Se estiver como Public, mude em Configurações → Rede e Internet → propriedades da rede → **Rede privada** (ou com o comando que o script mostra).
4. Na primeira vez que o servidor iniciar, o Windows pode perguntar se permite o acesso do programa à rede: marque **Redes privadas** e clique em **Permitir acesso**. Se clicar em Cancelar, o Windows cria uma regra de **bloqueio** para o programa, que vence a liberação da porta. Para desfazer, procure o programa em Painel de Controle → Firewall do Windows Defender → Permitir um aplicativo.

### 3. Roteador sem isolamento de clientes

Na rede usada pelos tablets (a principal, não a de visitantes), o isolamento de clientes ("AP Isolation", "Client Isolation", "Isolamento de AP") precisa estar **desligado**. Veja "Solução de problemas".

## Como acessar

- **No próprio computador servidor (caixa):** abra o navegador em `http://localhost:5000`, toque (ou clique) no seu nome e digite o PIN de 4 dígitos.
- **Nos tablets:**
  1. Conecte o tablet ao Wi-Fi do bar (a mesma rede do computador servidor).
  2. Abra o Chrome e digite o endereço mostrado na janela do servidor (ou na tela **Sobre**), ex.: `http://192.168.0.10:5000`.
  3. Toque no seu nome e digite o seu PIN de 4 dígitos no teclado da tela.
  4. Pronto: o sistema funciona normalmente numa aba comum do navegador. Instalar como app é opcional.
- **Nos celulares (opcional):** do mesmo jeito que no tablet, no Chrome do celular conectado ao Wi-Fi do bar. Na tela pequena, a comanda fica em duas abas ("Cardápio" e "Comanda"), com o total e o "Fechar Conta" sempre no rodapé.

### Abrir como aplicativo em tela cheia (opcional)

O navegador só oferece "Instalar app" e o modo tela cheia em conexões seguras (HTTPS ou `localhost`). Como os tablets acessam por `http://192.168.x.x`, isso pode não aparecer. Nada no sistema depende disso: numa aba comum tudo funciona igual. Duas formas de resolver:

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

1. **O servidor está rodando?** No próprio computador servidor, abra `http://localhost:5000`. Se não abrir, abra o servidor pelo atalho **Tucandeira Rock Bar** da Área de Trabalho. Se ele não abrir, veja o log em `C:\TucandeiraBar\dados\logs\servidor.log`.
2. **O servidor responde pelo IP da rede?** Ainda no computador servidor, abra `http://<IP-do-servidor>:5000` (ex.: `http://192.168.0.10:5000`). Se não abrir, confira o IP com `ipconfig` (para quem desenvolve: o `app.py` só escuta em `localhost`; use o `servidor.py`).
3. **Mesma rede?** O tablet precisa estar no mesmo Wi-Fi do servidor (não na rede de visitantes nem nos dados móveis). Confira também se o IP do servidor não mudou (por isso o IP fixo).
4. **Firewall do Windows:** a porta precisa estar liberada para redes **Privadas** (`scripts/liberar_firewall.ps1`, veja "Rede do bar") e a rede do bar precisa estar marcada como **Privada** no Windows. Confira também se não há uma regra de bloqueio para o programa (criada ao clicar em Cancelar no aviso do firewall).
5. **Isolamento de clientes no roteador:** se o tablet abre a página do roteador (ex.: `http://192.168.1.1`) mas não alcança o computador servidor em nenhuma porta — mesmo com o firewall do Windows desligado —, o roteador está impedindo que os aparelhos conversem entre si. É comum em roteadores de operadora e em redes de visitantes. O nome da opção varia: "Isolamento de AP", "AP Isolation", "Client Isolation", "Isolamento de clientes", "Wireless isolation".
   - **Solução:** desligar essa opção no roteador (na rede usada pelo bar, não na de visitantes) ou usar um roteador próprio para o sistema.
   - **Teste rápido para confirmar:** ligue o **Hotspot móvel** do Windows no computador servidor (Configurações → Rede e Internet → Hotspot móvel), conecte o tablet nesse hotspot e acesse `http://<IP-do-servidor-no-hotspot>:5000` (normalmente `http://192.168.137.1:5000`). Se funcionar pelo hotspot (com o firewall do Windows ligado e a regra do sistema criada), o problema é o roteador. O hotspot serve só como teste: não é a solução definitiva para o bar.

## Segurança

O sistema foi feito para uso **apenas na rede local do bar**. Não abra a porta no roteador nem exponha o servidor à internet. A sessão expira após um tempo sem uso, e as ações de gerente sempre pedem o PIN do gerente na hora.

## Para desenvolvedores

### Instalar

```
git clone https://github.com/marcianocamposgit/sistema_tucandeira-bar.git
cd sistema_tucandeira-bar
python -m pip install -r requirements.txt
```

O banco de dados é criado automaticamente em `data/tucandeira.db` na primeira execução, já com o cardápio inicial. No primeiro acesso, o sistema pede para criar o usuário gerente. Para começar com o banco limpo, basta **não** rodar o comando de dados de demonstração (abaixo).

### Iniciar o servidor

Servidor de produção (waitress, acessível pela rede local), o mesmo código do `TucandeiraBar.exe`:

```
python servidor.py                  # abre a janela do servidor e o navegador
python servidor.py --sem-janela     # só no console (QuickEdit desligado)
python servidor.py --sem-navegador  # não abre o navegador ao iniciar
```

Ao iniciar, mostra o endereço para acessar, por exemplo `http://192.168.0.10:5000`. A porta pode ser alterada em `config.py` (`PORTA`). Se o servidor já estiver aberto (porta ocupada), avisa e só abre o navegador. Log em `data/logs/servidor.log` (no bar, `C:\TucandeiraBar\dados\logs\`), com rotação.

Desenvolvimento (servidor do Flask com recarga automática — não usar no bar):

```
python app.py
```

Atalho para desenvolvedores no Windows: `iniciar.bat`, na raiz do projeto, encerra um servidor anterior que esteja usando a porta 5000 e inicia `python servidor.py --sem-janela`, que abre o navegador em `http://localhost:5000` (dá para abrir com dois cliques). Precisa do Python instalado; não é o instalador do bar.

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

### Gerar o executável e o pacote de entrega

```
powershell -ExecutionPolicy Bypass -File scripts\gerar_exe.ps1
```

Roda os testes, gera `dist\TucandeiraBar.exe` com o PyInstaller (receita versionada em `TucandeiraBar.spec`: um arquivo só, sem console, com templates, static e assets embutidos e o ícone da logo) e monta `dist\TucandeiraBar-<versão>\` e o `.zip` para levar ao bar (`scripts/montar_entrega.py`). Depois de trocar `assets/logo.png`, rode antes `python scripts/gerar_imagens.py`.

Para testar o executável sem tocar em `C:\TucandeiraBar\dados\`, aponte a pasta de dados para outro lugar com a variável `TUCANDEIRA_DADOS`.

> ⚠️ **Os PINs de demonstração nunca devem ser usados no bar.** Eles estão publicados aqui e servem só para testar no computador de desenvolvimento. No bar, cada pessoa cria o seu próprio PIN.

## Estrutura de pastas

```
tucandeira-bar/
├── app.py               # cria o app Flask (e roda o servidor de desenvolvimento)
├── servidor.py          # inicia o sistema com waitress na rede local (é também o TucandeiraBar.exe)
├── janela_servidor.py   # janela do servidor (Tkinter): endereços, backup, parar
├── TucandeiraBar.spec   # receita do PyInstaller para o executável
├── config.py            # número de mesas, porta, prazos, formas de pagamento, tempo de sessão, caminhos
├── database.py          # conexão SQLite (WAL), transações e criação das tabelas
├── models/              # classes de dados (Produto, Comanda, Venda...)
├── services/            # regras de negócio (usuários, produtos, caixa, comandas, pagamentos, relatórios, backup)
├── routes/              # rotas Flask (blueprints)
├── templates/           # páginas HTML (Jinja2)
├── static/              # CSS, JavaScript, fonte Anton, ícones e manifest do PWA
├── data/                # banco de dados e backups (não versionados)
├── assets/              # logo e imagens
├── scripts/             # imagens da logo, dados de demonstração, gerar o .exe, instalar, atualizar, firewall
├── legado_tkinter/      # versão antiga em Tkinter (só referência)
└── tests/               # testes automatizados (pytest)
```

## Autor

Marciano Campos
