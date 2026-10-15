/* ============================================================
   Tucandeira Rock Bar — tela de mesas: redesenha a grade com o
   estado vindo do servidor (/mesas/estado), sem recarregar a página.
   JavaScript ES5 para o Chrome antigo do tablet.
   ============================================================ */
(function () {
    'use strict';

    var tela = document.getElementById('tela-mesas');
    if (!tela || !window.TucandeiraRede) {
        return;
    }
    var rede = window.TucandeiraRede;
    var endereco = tela.getAttribute('data-endereco-estado');
    var segundos = parseFloat(tela.getAttribute('data-intervalo')) || 5;
    var situacao = tela.querySelector('[data-situacao-atualizacao]');
    var textoNormal = situacao ? situacao.textContent : '';
    var contadorBalcao = tela.querySelector('[data-balcao-contador]');
    var emAndamento = false;

    function escrever(elemento, campo, texto) {
        var alvo = elemento.querySelector('[data-campo="' + campo + '"]');
        if (alvo && alvo.textContent !== texto) {
            alvo.textContent = texto;
        }
    }

    function desenhar(dados) {
        for (var i = 0; i < dados.mesas.length; i++) {
            var mesa = dados.mesas[i];
            var elemento = tela.querySelector('[data-mesa="' + mesa.numero + '"]');
            if (!elemento) {
                continue;
            }
            elemento.className = 'mesa mesa-' + mesa.status;
            elemento.setAttribute('href', mesa.endereco);
            escrever(elemento, 'status_nome', mesa.status_nome);
            escrever(elemento, 'total', mesa.total);
            escrever(elemento, 'pessoas', mesa.pessoas_texto);
            escrever(elemento, 'juntas', mesa.juntas ? 'Mesas ' + mesa.juntas : '');
        }
        if (contadorBalcao) {
            contadorBalcao.textContent = dados.balcao_abertas;
            if (dados.balcao_abertas) {
                contadorBalcao.removeAttribute('hidden');
            } else {
                contadorBalcao.setAttribute('hidden', '');
            }
        }
    }

    function mostrarSituacao(semConexao) {
        if (!situacao) {
            return;
        }
        situacao.textContent = semConexao ? 'Sem conexão com o servidor. Tentando de novo...' : textoNormal;
        situacao.className = semConexao ? 'texto-alerta' : '';
    }

    function atualizar() {
        if (emAndamento) {
            return;
        }
        emAndamento = true;
        rede.pedir({
            endereco: endereco,
            automatica: true,
            aoTerminar: function (status, dados) {
                emAndamento = false;
                if (status === 200 && dados && dados.mesas) {
                    desenhar(dados);
                    mostrarSituacao(false);
                } else {
                    mostrarSituacao(true);
                }
            }
        });
    }

    rede.periodicamente(atualizar, segundos);
}());
