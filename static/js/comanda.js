/* ============================================================
   Tucandeira Rock Bar — tela da comanda.

   - Tocar no produto lança 1 unidade; "+" e "−" em cada linha.
     Cada toque vai na hora para o servidor (JSON); o botão fica
     desativado enquanto o pedido está em andamento.
   - Cada toque leva uma chave própria: se a rede falhar e o pedido
     for repetido, o servidor não lança duas vezes.
   - "−" depois do prazo: o servidor avisa e a tela abre o
     cancelamento (motivo + autorização do gerente).
   - A comanda se atualiza sozinha (itens lançados em outro aparelho).
   - Celular: abas "Cardápio" / "Comanda". Tablet e PC: lado a lado.

   JavaScript ES5 para o Chrome antigo do tablet.
   ============================================================ */
(function () {
    'use strict';

    var TEMPO_AVISO_MS = 3500;

    var tela = document.getElementById('comanda');
    if (!tela || !window.TucandeiraRede) {
        return;
    }
    var rede = window.TucandeiraRede;
    var csrf = tela.getAttribute('data-csrf');
    var enderecoEstado = tela.getAttribute('data-endereco-estado');
    var enderecoLancar = tela.getAttribute('data-endereco-lancar');
    var enderecoItens = tela.getAttribute('data-endereco-itens');
    var statusInicial = tela.getAttribute('data-status');
    var identificacaoInicial = tela.getAttribute('data-identificacao');
    var cardapioInicial = tela.getAttribute('data-cardapio');
    var segundos = parseFloat(tela.getAttribute('data-intervalo')) || 5;
    var corpo = tela.querySelector('[data-corpo]');
    var areaItens = tela.querySelector('[data-itens]');
    var aviso = tela.querySelector('[data-toast]');
    var ultimoHtmlItens = areaItens.innerHTML;
    var pedidosEmAndamento = 0;
    var temporizadorAviso = null;

    function todos(seletor, contexto) {
        return Array.prototype.slice.call((contexto || document).querySelectorAll(seletor));
    }

    function mostrar(elemento, visivel) {
        if (visivel) {
            elemento.removeAttribute('hidden');
        } else {
            elemento.setAttribute('hidden', '');
        }
    }

    function telaDeToque() {
        return !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
    }

    function novaChave() {
        return new Date().getTime().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
    }

    /* Sobe na árvore até achar o elemento com o atributo (Element.closest não existe no Chrome antigo). */
    function acima(elemento, atributo, limite) {
        while (elemento && elemento !== limite) {
            if (elemento.hasAttribute && elemento.hasAttribute(atributo)) {
                return elemento;
            }
            elemento = elemento.parentNode;
        }
        return null;
    }

    /* ---------- Aviso rápido (estoque, erro, item lançado) ---------- */
    function avisar(texto, tipo) {
        aviso.textContent = texto;
        aviso.className = 'toast toast-' + (tipo || 'info');
        mostrar(aviso, true);
        clearTimeout(temporizadorAviso);
        temporizadorAviso = setTimeout(function () {
            mostrar(aviso, false);
        }, TEMPO_AVISO_MS);
    }

    /* ---------- Quadros (observação, pessoas, transferir...) ---------- */
    function quadroAberto() {
        return todos('.sobreposicao').some(function (quadro) {
            return !quadro.hasAttribute('hidden');
        });
    }

    function abrirQuadro(id) {
        var quadro = document.getElementById(id);
        if (!quadro) {
            return null;
        }
        mostrar(quadro, true);
        var campo = quadro.querySelector('input[type="text"]');
        if (campo && !telaDeToque()) {
            campo.focus();  // no PC já dá para digitar; no tablet não abre o teclado sozinho
        }
        return quadro;
    }

    function fecharQuadros() {
        todos('.sobreposicao[id^="quadro-"]').forEach(function (quadro) {
            mostrar(quadro, false);
        });
    }

    function iniciarQuadros() {
        todos('[data-abrir]').forEach(function (botao) {
            botao.addEventListener('click', function () {
                abrirQuadro(botao.getAttribute('data-abrir'));
            });
        });
        todos('[data-fechar-quadro]').forEach(function (botao) {
            botao.addEventListener('click', fecharQuadros);
        });
        document.addEventListener('keydown', function (evento) {
            if (evento.key === 'Escape' || evento.keyCode === 27) {
                fecharQuadros();
            }
        });
        todos('[data-confirmar]').forEach(function (botao) {
            botao.addEventListener('click', function (evento) {
                if (!window.confirm(botao.getAttribute('data-confirmar'))) {
                    evento.preventDefault();
                }
            });
        });
    }

    function abrirObservacao(botao) {
        var quadro = document.getElementById('quadro-observacao');
        quadro.querySelector('input[name="item_id"]').value = botao.getAttribute('data-item');
        quadro.querySelector('input[name="observacao"]').value = botao.getAttribute('data-observacao') || '';
        quadro.querySelector('[data-nome-item]').textContent = botao.getAttribute('data-nome');
        abrirQuadro('quadro-observacao');
    }

    function abrirCancelarItem(itemId, nome) {
        var quadro = document.getElementById('quadro-cancelar-item');
        var formulario = quadro.querySelector('form');
        formulario.querySelector('input[name="item_id"]').value = itemId;
        formulario.setAttribute('data-exige-gerente', 'Cancelar 1 × ' + nome);
        quadro.querySelector('[data-nome-item]').textContent = '1 × ' + nome;
        abrirQuadro('quadro-cancelar-item');
    }

    /* ---------- Desenhar a comanda com o estado do servidor ---------- */
    function escrever(campo, texto) {
        todos('[data-campo="' + campo + '"]', tela).forEach(function (elemento) {
            if (elemento.textContent !== String(texto)) {
                elemento.textContent = texto;
            }
        });
    }

    function desenhar(dados) {
        if (dados.status !== statusInicial || dados.identificacao !== identificacaoInicial ||
                (dados.cardapio && dados.cardapio !== cardapioInicial)) {
            // Outro aparelho pediu a conta, transferiu, juntou mesas ou mudou o cardápio: recarrega a tela.
            if (!quadroAberto() && !pedidosEmAndamento) {
                window.location.reload();
            }
            return;
        }
        if (dados.itens_html !== ultimoHtmlItens) {
            areaItens.innerHTML = dados.itens_html;
            ultimoHtmlItens = dados.itens_html;
        }
        escrever('itens_texto', dados.itens_texto);
        escrever('pessoas_texto', dados.pessoas_texto);
        escrever('total', dados.total);
        escrever('pago', dados.pago);
        escrever('saldo', dados.saldo);
        mostrar(tela.querySelector('[data-pago-linha]'), !!dados.pago);
        atualizarCancelarComanda(dados.tem_itens);
    }

    /* Sem itens, o operador cancela sozinho; com itens, pede o gerente. */
    function atualizarCancelarComanda(temItens) {
        var quadro = document.getElementById('quadro-cancelar-comanda');
        if (!quadro || quadroAberto()) {
            return;
        }
        var formulario = quadro.querySelector('form');
        if (temItens) {
            formulario.setAttribute('data-exige-gerente', formulario.getAttribute('data-texto-gerente'));
        } else {
            formulario.removeAttribute('data-exige-gerente');
        }
        mostrar(quadro.querySelector('[data-cancelar-com-itens]'), temItens);
        mostrar(quadro.querySelector('[data-cancelar-sem-itens]'), !temItens);
    }

    /* Resposta de qualquer pedido: comanda fechada, caixa fechado, erro ou estado novo. */
    function tratar(status, dados) {
        if (!dados) {
            avisar('Sem resposta do servidor. Confira o Wi-Fi e tente de novo.', 'erro');
            return false;
        }
        if (dados.caixa_fechado) {
            avisar(dados.erro, 'erro');
            setTimeout(function () {
                window.location.reload();
            }, 1500);
            return false;
        }
        if (dados.fechada) {
            avisar(dados.erro || 'Esta comanda já foi fechada.', 'erro');
            setTimeout(function () {
                window.location.href = dados.ir_para;
            }, 1800);
            return false;
        }
        desenhar(dados);
        if (dados.erro) {
            avisar(dados.erro, 'erro');
            return false;
        }
        if (dados.aviso) {
            avisar(dados.aviso, 'aviso');
        }
        return status === 200;
    }

    /* ---------- Ações: lançar, "+", "−" ---------- */
    function enviar(botao, endereco, dados, tentativas, depois) {
        if (botao.disabled) {
            return;  // toque duplo
        }
        botao.disabled = true;
        pedidosEmAndamento += 1;
        dados = dados || {};
        rede.pedir({
            metodo: 'POST',
            endereco: endereco,
            dados: dados,
            csrf: csrf,
            tentativas: tentativas,
            aoTerminar: function (status, resposta) {
                pedidosEmAndamento -= 1;
                botao.disabled = false;
                var ok = tratar(status, resposta);
                if (depois) {
                    depois(ok, resposta);
                }
            }
        });
    }

    function iniciarCardapio() {
        todos('[data-categoria]', tela).forEach(function (aba) {
            aba.addEventListener('click', function () {
                var id = aba.getAttribute('data-categoria');
                todos('[data-categoria]', tela).forEach(function (outra) {
                    outra.classList.toggle('aba-ativa', outra === aba);
                });
                todos('[data-produtos-categoria]', tela).forEach(function (lista) {
                    mostrar(lista, lista.getAttribute('data-produtos-categoria') === id);
                });
            });
        });
        todos('[data-produto]', tela).forEach(function (botao) {
            botao.addEventListener('click', function () {
                var nome = botao.querySelector('.produto-nome').textContent;
                // Mesma chave nas repetições automáticas: o servidor não lança duas vezes.
                enviar(botao, enderecoLancar, {produto_id: botao.getAttribute('data-produto'), chave: novaChave()}, 3,
                    function (ok, resposta) {
                        if (ok && !(resposta && resposta.aviso)) {
                            avisar('+1 ' + nome, 'sucesso');
                        }
                    });
            });
        });
    }

    function iniciarItens() {
        // Os itens são redesenhados a cada atualização: um ouvinte só, na área toda.
        areaItens.addEventListener('click', function (evento) {
            var botao = acima(evento.target, 'data-acao', areaItens);
            if (!botao) {
                return;
            }
            var acao = botao.getAttribute('data-acao');
            var itemId = botao.getAttribute('data-item');
            if (acao === 'observacao') {
                abrirObservacao(botao);
            } else if (acao === 'mais') {
                enviar(botao, enderecoItens + itemId + '/mais', {chave: novaChave()}, 3);
            } else if (acao === 'menos') {
                var nome = botao.getAttribute('data-nome');
                // "−" não repete sozinho: um reenvio poderia tirar duas unidades.
                enviar(botao, enderecoItens + itemId + '/menos', null, 1, function (ok, resposta) {
                    if (resposta && resposta.precisa_cancelar) {
                        abrirCancelarItem(resposta.item_id, nome);
                    }
                });
            }
        });
    }

    /* ---------- Abas do celular: Cardápio / Comanda ---------- */
    function iniciarAbas() {
        var abas = todos('.abas-comanda [data-aba]', tela);
        function escolher(nome) {
            corpo.className = 'comanda-corpo mostrar-' + nome;
            abas.forEach(function (aba) {
                aba.classList.toggle('aba-ativa', aba.getAttribute('data-aba') === nome);
            });
        }
        abas.forEach(function (aba) {
            aba.addEventListener('click', function () {
                escolher(aba.getAttribute('data-aba'));
            });
        });
        escolher(corpo.className.indexOf('mostrar-comanda') >= 0 ? 'comanda' : 'cardapio');
    }

    /* ---------- Atualização automática ---------- */
    function atualizar() {
        if (pedidosEmAndamento) {
            return;  // a resposta do pedido já traz o estado novo
        }
        rede.pedir({
            endereco: enderecoEstado,
            automatica: true,
            aoTerminar: function (status, dados) {
                if (dados && !pedidosEmAndamento) {
                    tratar(status, dados);
                }
            }
        });
    }

    iniciarQuadros();
    iniciarCardapio();
    iniciarItens();
    iniciarAbas();
    rede.periodicamente(atualizar, segundos);
}());
