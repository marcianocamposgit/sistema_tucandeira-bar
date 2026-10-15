/* ============================================================
   Tucandeira Rock Bar — campos de dinheiro com teclado na tela
   e botões de atalho para textos curtos (motivo).

   - No tablet (toque), o campo fica só para leitura, para não abrir
     o teclado do Android: os números entram pelo teclado da tela.
   - No computador (mouse), o campo aceita digitação normal e o
     teclado da tela também funciona.
   O servidor sempre valida o valor; aqui é só a digitação.

   JavaScript ES5 para o Chrome antigo do tablet.
   ============================================================ */
(function () {
    'use strict';

    var MAXIMO_DIGITOS_REAIS = 7;  // até R$ 9.999.999

    function todos(seletor, contexto) {
        return Array.prototype.slice.call((contexto || document).querySelectorAll(seletor));
    }

    function telaDeToque() {
        if (window.matchMedia && window.matchMedia('(pointer: coarse)').matches) {
            return true;
        }
        return !window.matchMedia && 'ontouchstart' in window;
    }

    /* Aplica uma tecla ao texto atual, no formato "1234,56" (ou "12" em quantidades). */
    function aplicarTecla(texto, tecla, inteiro) {
        var virgula = texto.indexOf(',');
        if (tecla === 'limpar') {
            return '';
        }
        if (tecla === 'apagar') {
            return texto.slice(0, -1);
        }
        if (inteiro) {
            if (tecla === ',' || texto.length >= 6) {
                return texto;  // quantidade: sem vírgula, até 6 dígitos
            }
            return texto === '0' ? tecla : texto + tecla;
        }
        if (tecla === ',') {
            return virgula >= 0 ? texto : (texto || '0') + ',';
        }
        if (virgula >= 0) {
            return texto.length - virgula > 2 ? texto : texto + tecla;  // no máximo 2 casas
        }
        if (texto === '0') {
            return tecla;
        }
        if (texto.replace(/\D/g, '').length >= MAXIMO_DIGITOS_REAIS) {
            return texto;
        }
        return texto + tecla;
    }

    /* Formulário em volta do elemento (Element.closest não existe no Chrome antigo). */
    function formularioDe(elemento) {
        while (elemento && elemento.tagName !== 'FORM') {
            elemento = elemento.parentNode;
        }
        return elemento;
    }

    function iniciarCamposValor() {
        var campos = todos('.entrada-valor');
        var teclados = todos('[data-teclado-valor]');
        if (!campos.length) {
            return;
        }
        var toque = telaDeToque();
        var ativo = null;

        function ativar(campo) {
            if (ativo) {
                ativo.parentNode.parentNode.classList.remove('campo-ativo');
            }
            ativo = campo;
            ativo.parentNode.parentNode.classList.add('campo-ativo');
        }

        campos.forEach(function (campo) {
            if (toque) {
                campo.readOnly = true;
            }
            campo.addEventListener('focus', function () {
                ativar(campo);
            });
            campo.addEventListener('click', function () {
                ativar(campo);
            });
        });

        var inicial = document.querySelector('.entrada-valor[data-foco]') || campos[0];
        ativar(inicial);
        if (!toque && !document.querySelector('[autofocus]')) {
            inicial.focus();  // se outro campo pediu o foco (ex.: nome do produto), ele fica com o foco
        }

        /* Cada teclado escreve no campo selecionado do próprio formulário
           (ex.: tela de pagamento e quadro de desconto, cada um com o seu). */
        function campoDoTeclado(teclado) {
            var formulario = formularioDe(teclado);
            if (!formulario || formulario.contains(ativo)) {
                return ativo;
            }
            var primeiro = formulario.querySelector('.entrada-valor');
            if (primeiro) {
                ativar(primeiro);
            }
            return ativo;
        }

        teclados.forEach(function (teclado) {
            todos('[data-tecla-valor]', teclado).forEach(function (botao) {
                botao.addEventListener('click', function () {
                    var campo = campoDoTeclado(teclado);
                    campo.value = aplicarTecla(campo.value, botao.getAttribute('data-tecla-valor'),
                        campo.hasAttribute('data-inteiro'));
                    if (!toque) {
                        campo.focus();  // no computador, Enter continua enviando o formulário
                    }
                });
            });
        });
    }

    function iniciarAtalhos() {
        todos('[data-atalho]').forEach(function (botao) {
            botao.addEventListener('click', function () {
                var formulario = botao.form || document;
                var campo = formulario.querySelector('input[name="' + botao.getAttribute('data-alvo') + '"]');
                if (campo) {
                    campo.value = botao.getAttribute('data-atalho');
                }
            });
        });
    }

    iniciarCamposValor();
    iniciarAtalhos();
}());
