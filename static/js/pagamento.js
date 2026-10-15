/* ============================================================
   Tucandeira Rock Bar — tela de pagamento (fechar conta).

   - Forma de pagamento: o campo "dinheiro recebido" só aparece em Dinheiro.
   - Atalhos: "Saldo inteiro" e "1 pessoa" preenchem o valor a pagar;
     as cédulas (+ R$ 10, 20, 50, 100) somam no dinheiro recebido.
   - Quadros de estorno e desconto (o envio pede o gerente, em pin.js).
   - Se outro aparelho mexer na conta (lançar item, pagar), a tela se
     atualiza sozinha, ou avisa se já houver algo digitado.
   Os valores e o troco de verdade são sempre calculados no servidor.

   JavaScript ES5 para o Chrome antigo do tablet.
   ============================================================ */
(function () {
    'use strict';

    var tela = document.getElementById('pagamento');
    if (!tela) {
        return;
    }
    var formulario = tela.querySelector('[data-form-receber]');

    function todos(seletor, contexto) {
        return Array.prototype.slice.call((contexto || document).querySelectorAll(seletor));
    }

    function mostrar(elemento, visivel) {
        if (!elemento) {
            return;
        }
        if (visivel) {
            elemento.removeAttribute('hidden');
        } else {
            elemento.setAttribute('hidden', '');
        }
    }

    function telaDeToque() {
        return !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
    }

    function campo(nome) {
        return formulario ? formulario.querySelector('input[name="' + nome + '"]') : null;
    }

    /* Dá foco ao campo (no PC) para o teclado da tela e o físico escreverem nele. */
    function selecionar(entrada) {
        if (entrada && !telaDeToque()) {
            entrada.focus();
        } else if (entrada) {
            entrada.click();  // no tablet: só marca o campo ativo, sem abrir o teclado do Android
        }
    }

    /* ---------- Forma de pagamento ---------- */
    function iniciarFormas() {
        if (!formulario) {
            return;
        }
        var soDinheiro = formulario.querySelector('[data-so-dinheiro]');
        function atualizar() {
            var marcada = formulario.querySelector('input[name="forma"]:checked');
            var dinheiro = !!marcada && marcada.value === 'dinheiro';
            mostrar(soDinheiro, dinheiro);
            todos('.forma-pagamento', formulario).forEach(function (rotulo) {
                rotulo.classList.toggle('forma-escolhida', rotulo.querySelector('input').checked);
            });
        }
        todos('input[name="forma"]', formulario).forEach(function (opcao) {
            opcao.addEventListener('change', atualizar);
        });
        atualizar();
    }

    /* ---------- Atalhos de valor e cédulas ---------- */
    function centavos(texto) {
        var limpo = (texto || '').replace(/[^\d,]/g, '');
        var partes = limpo.split(',');
        var reais = parseInt(partes[0] || '0', 10) || 0;
        var resto = ((partes[1] || '') + '00').slice(0, 2);
        return reais * 100 + (parseInt(resto, 10) || 0);
    }

    function textoDeCentavos(valor) {
        var resto = valor % 100;
        return Math.floor(valor / 100) + ',' + (resto < 10 ? '0' : '') + resto;
    }

    function iniciarAtalhos() {
        if (!formulario) {
            return;
        }
        todos('[data-preencher]', formulario).forEach(function (botao) {
            botao.addEventListener('click', function () {
                var alvo = campo(botao.getAttribute('data-preencher'));
                alvo.value = botao.getAttribute('data-texto');
                selecionar(alvo);
            });
        });
        todos('[data-cedula]', formulario).forEach(function (botao) {
            botao.addEventListener('click', function () {
                var recebido = campo('recebido');
                var soma = centavos(recebido.value) + parseInt(botao.getAttribute('data-cedula'), 10) * 100;
                recebido.value = textoDeCentavos(soma);
                selecionar(recebido);
            });
        });
    }

    /* ---------- Quadros (estorno e desconto) ---------- */
    function quadroAberto() {
        return todos('.sobreposicao').some(function (quadro) {
            return !quadro.hasAttribute('hidden');
        });
    }

    function abrirQuadro(id) {
        var quadro = document.getElementById(id);
        mostrar(quadro, true);
        var primeiro = quadro && quadro.querySelector('input[type="text"]');
        if (primeiro && !telaDeToque()) {
            primeiro.focus();
        }
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
        todos('[data-estornar]').forEach(function (botao) {
            botao.addEventListener('click', function () {
                var quadro = document.getElementById('quadro-estorno');
                quadro.querySelector('input[name="pagamento_id"]').value = botao.getAttribute('data-estornar');
                quadro.querySelector('[data-descricao-pagamento]').textContent = botao.getAttribute('data-descricao');
                quadro.querySelector('form').setAttribute('data-exige-gerente',
                    'Estornar ' + botao.getAttribute('data-descricao'));
                abrirQuadro('quadro-estorno');
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
    }

    /* ---------- Conta mudou em outro aparelho ---------- */
    function algoDigitado() {
        if (!formulario) {
            return false;
        }
        return !!(campo('valor').value || (campo('recebido') && campo('recebido').value) ||
            formulario.querySelector('input[name="forma"]:checked'));
    }

    function iniciarAtualizacao() {
        if (!window.TucandeiraRede) {
            return;
        }
        var rede = window.TucandeiraRede;
        var endereco = tela.getAttribute('data-endereco-estado');
        var total = tela.getAttribute('data-total');
        var saldo = tela.getAttribute('data-saldo');
        var aviso = tela.querySelector('[data-conta-mudou]');
        var segundos = parseFloat(tela.getAttribute('data-intervalo')) || 5;
        var enviando = false;

        todos('form').forEach(function (f) {
            f.addEventListener('submit', function () {
                enviando = true;
            });
        });

        rede.periodicamente(function () {
            if (enviando) {
                return;
            }
            rede.pedir({
                endereco: endereco,
                automatica: true,
                aoTerminar: function (status, dados) {
                    if (!dados || enviando) {
                        return;
                    }
                    var mudou = dados.fechada || dados.total !== total || dados.saldo !== saldo;
                    if (!mudou) {
                        return;
                    }
                    if (!quadroAberto() && !algoDigitado()) {
                        window.location.reload();  // o servidor mostra a conta nova (ou "conta paga")
                    } else {
                        mostrar(aviso, true);
                    }
                }
            });
        }, segundos);
    }

    iniciarFormas();
    iniciarAtalhos();
    iniciarQuadros();
    iniciarAtualizacao();
}());
