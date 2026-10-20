/* ============================================================
   Tucandeira Rock Bar — teclado de PIN, login, autorização do
   gerente, proteção contra toque duplo, fim de sessão, campo de
   texto visível com o teclado virtual e registro do PWA.
   (Carregado em todas as telas.)

   JavaScript ES5 para o Chrome antigo do tablet: sem let/const,
   arrow functions, fetch, NodeList.forEach, Element.closest.
   ============================================================ */
(function () {
    'use strict';

    var TAMANHO_PIN = 4;

    function todos(seletor, contexto) {
        return Array.prototype.slice.call((contexto || document).querySelectorAll(seletor));
    }

    function um(seletor, contexto) {
        return (contexto || document).querySelector(seletor);
    }

    function mostrar(elemento, visivel) {
        if (visivel) {
            elemento.removeAttribute('hidden');
        } else {
            elemento.setAttribute('hidden', '');
        }
    }

    function pintarPontos(pontos, quantos) {
        for (var i = 0; i < pontos.length; i++) {
            pontos[i].className = i < quantos ? 'cheio' : '';
        }
    }

    /* ---------- Entrada de PIN: pontos + teclado na tela ---------- */
    var entradasPin = [];

    function EntradaPin(container, aoCompletar) {
        var self = this;
        this.valor = '';
        this.travado = false;
        this.container = container;
        this.pontos = todos('.pin-pontos span', container);
        this.aoCompletar = aoCompletar;
        entradasPin.push(this);
        todos('.tecla', container).forEach(function (botao) {
            botao.addEventListener('click', function () {
                self.tecla(botao.getAttribute('data-tecla'));
            });
        });
    }

    EntradaPin.prototype.tecla = function (tecla) {
        var self = this;
        if (this.travado) {
            return;
        }
        if (tecla === 'apagar') {
            this.valor = this.valor.slice(0, -1);
        } else if (tecla === 'limpar') {
            this.valor = '';
        } else if (this.valor.length < TAMANHO_PIN) {
            this.valor += tecla;
        }
        pintarPontos(this.pontos, this.valor.length);
        if (this.valor.length === TAMANHO_PIN) {
            this.travado = true;
            // Pequena pausa para a pessoa ver o 4º ponto preenchido.
            setTimeout(function () {
                self.aoCompletar(self.valor);
            }, 150);
        }
    };

    EntradaPin.prototype.zerar = function () {
        this.valor = '';
        this.travado = false;
        pintarPontos(this.pontos, 0);
    };

    /* No PC: dígitos e Backspace do teclado físico vão para o teclado de PIN visível. */
    function iniciarTecladoFisico() {
        document.addEventListener('keydown', function (evento) {
            var visivel = null;
            for (var i = entradasPin.length - 1; i >= 0; i--) {
                if (entradasPin[i].container.offsetHeight > 0) {  // não está escondido
                    visivel = entradasPin[i];
                    break;
                }
            }
            if (!visivel || evento.ctrlKey || evento.altKey || evento.metaKey) {
                return;
            }
            var tecla = evento.key;
            if (tecla && tecla.length === 1 && tecla >= '0' && tecla <= '9') {
                visivel.tecla(tecla);
            } else if (tecla === 'Backspace') {
                visivel.tecla('apagar');
            } else {
                return;
            }
            evento.preventDefault();
        });
    }

    /* ---------- Formulários: campo oculto e botões ---------- */
    function campoOculto(formulario, nome, valor) {
        var campo = formulario.querySelector('input[name="' + nome + '"]');
        if (!campo) {
            campo = document.createElement('input');
            campo.type = 'hidden';
            campo.name = nome;
            formulario.appendChild(campo);
        }
        campo.value = valor;
    }

    function desativarBotoes(formulario, desativar) {
        todos('button, input[type="submit"]', formulario).forEach(function (botao) {
            botao.disabled = desativar;
        });
    }

    function enviar(formulario) {
        formulario.setAttribute('data-enviando', '1');
        desativarBotoes(formulario, true);
        formulario.submit();
    }

    /* ---------- Login: escolher o nome e digitar o PIN ---------- */
    function iniciarLogin() {
        var login = document.getElementById('login');
        if (!login) {
            return;
        }
        var etapaNomes = um('[data-etapa="nomes"]', login);
        var etapaPin = um('[data-etapa="pin"]', login);
        var formulario = um('[data-formulario-login]', login);
        var nomeEscolhido = um('[data-nome-escolhido]', login);

        var entrada = new EntradaPin(etapaPin, function (pin) {
            formulario.querySelector('input[name="pin"]').value = pin;
            formulario.submit();
        });

        function escolher(botao) {
            formulario.querySelector('input[name="usuario_id"]').value = botao.getAttribute('data-usuario-id');
            nomeEscolhido.textContent = botao.getAttribute('data-nome');
            entrada.zerar();
            mostrar(etapaNomes, false);
            mostrar(etapaPin, true);
        }

        todos('[data-usuario-id]', etapaNomes).forEach(function (botao) {
            botao.addEventListener('click', function () {
                escolher(botao);
            });
        });
        um('[data-voltar]', etapaPin).addEventListener('click', function () {
            entrada.zerar();
            mostrar(etapaPin, false);
            mostrar(etapaNomes, true);
        });

        // Depois de um PIN errado, volta direto para o teclado da mesma pessoa.
        var selecionado = login.getAttribute('data-selecionado');
        if (selecionado) {
            var botao = um('[data-usuario-id="' + selecionado + '"]', etapaNomes);
            if (botao) {
                escolher(botao);
            }
        }
    }

    /* ---------- Campos de PIN em formulários (teclado flutuante) ---------- */
    function marcarCampoPin(campo) {
        var valor = um('input', campo).value;
        pintarPontos(todos('.pin-pontos span', campo), valor.length);
        campo.classList.toggle('campo-preenchido', valor.length === TAMANHO_PIN);
    }

    function iniciarCamposPin() {
        var quadro = document.getElementById('teclado-flutuante');
        if (!quadro) {
            return;
        }
        var titulo = um('[data-titulo]', quadro);
        var campoAtual = null;

        function fechar() {
            mostrar(quadro, false);
            campoAtual = null;
        }

        var entrada = new EntradaPin(quadro, function (pin) {
            um('input', campoAtual).value = pin;
            marcarCampoPin(campoAtual);
            fechar();
        });

        todos('.campo-pin').forEach(function (campo) {
            um('.campo-pin-mostrador', campo).addEventListener('click', function () {
                campoAtual = campo;
                campo.classList.remove('campo-erro');
                titulo.textContent = campo.getAttribute('data-rotulo');
                entrada.zerar();
                mostrar(quadro, true);
            });
        });
        um('[data-fechar]', quadro).addEventListener('click', fechar);
    }

    function pinsCompletos(formulario) {
        var ok = true;
        todos('.campo-pin', formulario).forEach(function (campo) {
            if (um('input', campo).value.length !== TAMANHO_PIN) {
                campo.classList.add('campo-erro');
                ok = false;
            }
        });
        return ok;
    }

    /* ---------- Autorização do gerente ---------- */
    var autorizacao = null;

    function iniciarAutorizacao() {
        var quadro = document.getElementById('autorizacao-gerente');
        if (!quadro) {
            return;
        }
        var etapaEscolher = um('[data-etapa="escolher"]', quadro);
        var etapaPin = um('[data-etapa="pin"]', quadro);
        var textoAcao = um('[data-acao]', quadro);
        var nomeGerente = um('[data-gerente-escolhido]', quadro);
        var botoesGerente = todos('[data-gerente-id]', quadro);
        var formularioAtual = null;
        var gerenteId = null;

        function fechar() {
            mostrar(quadro, false);
            formularioAtual = null;
        }

        var entrada = new EntradaPin(etapaPin, function (pin) {
            campoOculto(formularioAtual, 'gerente_id', gerenteId);
            campoOculto(formularioAtual, 'pin_gerente', pin);
            var formulario = formularioAtual;
            fechar();
            enviar(formulario);
        });

        function escolher(botao) {
            gerenteId = botao.getAttribute('data-gerente-id');
            nomeGerente.textContent = botao.getAttribute('data-gerente-nome');
            entrada.zerar();
            mostrar(etapaEscolher, false);
            mostrar(etapaPin, true);
        }

        botoesGerente.forEach(function (botao) {
            botao.addEventListener('click', function () {
                escolher(botao);
            });
        });
        um('[data-fechar]', quadro).addEventListener('click', fechar);

        autorizacao = {
            abrir: function (formulario) {
                formularioAtual = formulario;
                textoAcao.textContent = formulario.getAttribute('data-exige-gerente') || '';
                entrada.zerar();
                if (botoesGerente.length === 1) {
                    escolher(botoesGerente[0]);  // um só gerente: vai direto para o PIN
                } else {
                    mostrar(etapaPin, false);
                    mostrar(etapaEscolher, true);
                }
                mostrar(quadro, true);
            }
        };
    }

    /* ---------- Envio de formulários (validação, gerente, toque duplo) ---------- */
    function iniciarFormularios() {
        todos('form').forEach(function (formulario) {
            formulario.addEventListener('submit', function (evento) {
                if (formulario.getAttribute('data-enviando')) {
                    evento.preventDefault();  // toque duplo
                    return;
                }
                if (formulario.hasAttribute('data-validar-pin') && !pinsCompletos(formulario)) {
                    evento.preventDefault();
                    return;
                }
                if (formulario.hasAttribute('data-exige-gerente') && autorizacao) {
                    evento.preventDefault();
                    autorizacao.abrir(formulario);
                    return;
                }
                formulario.setAttribute('data-enviando', '1');
                setTimeout(function () {
                    desativarBotoes(formulario, true);
                }, 0);
            });
        });

        // Ao voltar pelo botão "voltar" do navegador, reativa os botões.
        window.addEventListener('pageshow', function () {
            todos('form[data-enviando]').forEach(function (formulario) {
                formulario.removeAttribute('data-enviando');
                desativarBotoes(formulario, false);
            });
        });
    }

    /* ---------- Fim da sessão por inatividade ---------- */
    function iniciarSessao() {
        var minutos = parseFloat(document.body.getAttribute('data-tempo-sessao'));
        if (!minutos) {
            return;
        }
        var espera = (minutos * 60 + 5) * 1000;
        var temporizador = null;

        function reiniciar() {
            clearTimeout(temporizador);
            temporizador = setTimeout(function () {
                // O servidor já considera a sessão expirada e mostra o login.
                window.location.href = '/';
            }, espera);
        }

        ['click', 'touchstart', 'keydown'].forEach(function (tipo) {
            document.addEventListener(tipo, reiniciar, true);
        });
        reiniciar();
    }

    /* ---------- Campo de texto visível acima do teclado virtual ---------- */
    function iniciarCampoVisivel() {
        // Só em aparelhos de toque: no PC não há teclado virtual e a página não deve pular.
        if (!('ontouchstart' in window) && !(navigator.maxTouchPoints > 0)) {
            return;
        }
        document.addEventListener('focusin', function (evento) {
            var campo = evento.target;
            var tipo = (campo.getAttribute && campo.getAttribute('type')) || '';
            if (!(campo.tagName === 'TEXTAREA' || (campo.tagName === 'INPUT' && tipo !== 'hidden' &&
                    tipo !== 'radio' && tipo !== 'checkbox' && !campo.readOnly))) {
                return;
            }
            // Espera o teclado abrir (a tela encolhe) e traz o campo para o meio da área visível.
            setTimeout(function () {
                if (document.activeElement !== campo || !campo.scrollIntoView) {
                    return;
                }
                try {
                    campo.scrollIntoView({block: 'center'});
                } catch (erro) {
                    campo.scrollIntoView(false);  // Chrome antigo: só aceita true/false
                }
            }, 350);
        });
    }

    /* ---------- PWA (opcional) ----------
       Só em contexto seguro (HTTPS, localhost ou o endereço liberado no
       chrome://flags). Sem ele, ou se falhar, a página funciona igual. */
    function registrarServiceWorker() {
        try {
            if (window.isSecureContext && 'serviceWorker' in navigator) {
                navigator.serviceWorker.register('/sw.js')['catch'](function () {});
            }
        } catch (erro) {
            // Nunca quebra a página.
        }
    }

    iniciarLogin();
    iniciarCamposPin();
    iniciarAutorizacao();
    iniciarFormularios();
    iniciarSessao();
    iniciarTecladoFisico();
    iniciarCampoVisivel();
    registrarServiceWorker();
}());
