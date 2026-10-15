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

    /* Aplica uma tecla ao texto atual, no formato "1234,56". */
    function aplicarTecla(texto, tecla) {
        var virgula = texto.indexOf(',');
        if (tecla === 'limpar') {
            return '';
        }
        if (tecla === 'apagar') {
            return texto.slice(0, -1);
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

    function iniciarCamposValor() {
        var campos = todos('.entrada-valor');
        var teclado = document.querySelector('[data-teclado-valor]');
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
        if (!toque) {
            inicial.focus();
        }

        if (!teclado) {
            return;
        }
        todos('[data-tecla-valor]', teclado).forEach(function (botao) {
            botao.addEventListener('click', function () {
                ativo.value = aplicarTecla(ativo.value, botao.getAttribute('data-tecla-valor'));
                if (!toque) {
                    ativo.focus();  // no computador, Enter continua enviando o formulário
                }
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
