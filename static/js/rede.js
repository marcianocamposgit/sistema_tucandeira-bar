/* ============================================================
   Tucandeira Rock Bar — pedidos ao servidor e atualização automática
   (usado pelas telas de mesas e de comanda).

   - pedir(): XMLHttpRequest com JSON, CSRF e repetição em caso de
     falha de rede (só para pedidos que podem repetir sem duplicar).
   - periodicamente(): chama a função a cada N segundos e pausa com a
     aba em segundo plano; ao voltar, atualiza na hora.

   JavaScript ES5 para o Chrome antigo do tablet (sem fetch, sem promessas).
   ============================================================ */
(function () {
    'use strict';

    var ESPERA_MAXIMA_MS = 8000;
    var PAUSA_ENTRE_TENTATIVAS_MS = 700;

    function codificar(dados) {
        var partes = [];
        for (var chave in dados) {
            if (Object.prototype.hasOwnProperty.call(dados, chave)) {
                partes.push(encodeURIComponent(chave) + '=' + encodeURIComponent(dados[chave]));
            }
        }
        return partes.join('&');
    }

    /* opcoes: metodo, endereco, dados (objeto), csrf, automatica (bool),
       tentativas (padrão 1), aoTerminar(status, json ou null). */
    function pedir(opcoes) {
        var corpo = opcoes.dados ? codificar(opcoes.dados) : null;

        function tentar(restantes) {
            var xhr = new XMLHttpRequest();
            xhr.open(opcoes.metodo || 'GET', opcoes.endereco, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.setRequestHeader('Accept', 'application/json');
            if (opcoes.automatica) {
                xhr.setRequestHeader('X-Atualizacao-Automatica', '1');  // não renova a sessão
            }
            if (opcoes.csrf) {
                xhr.setRequestHeader('X-CSRF-Token', opcoes.csrf);
            }
            if (corpo !== null) {
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            }
            xhr.timeout = ESPERA_MAXIMA_MS;
            xhr.onreadystatechange = function () {
                if (xhr.readyState !== 4) {
                    return;
                }
                if (xhr.status === 0 && restantes > 1) {  // sem resposta (Wi-Fi): tenta de novo
                    setTimeout(function () {
                        tentar(restantes - 1);
                    }, PAUSA_ENTRE_TENTATIVAS_MS);
                    return;
                }
                if (xhr.status === 401) {  // sessão expirou: a página mostra o login
                    window.location.reload();
                    return;
                }
                var json = null;
                try {
                    json = JSON.parse(xhr.responseText);
                } catch (erro) {
                    json = null;
                }
                opcoes.aoTerminar(xhr.status, json);
            };
            xhr.send(corpo);
        }

        tentar(opcoes.tentativas || 1);
    }

    function propriedadeOculto() {
        if ('hidden' in document) {
            return ['hidden', 'visibilitychange'];
        }
        if ('webkitHidden' in document) {
            return ['webkitHidden', 'webkitvisibilitychange'];
        }
        return [null, null];
    }

    function periodicamente(funcao, segundos) {
        var nomes = propriedadeOculto();
        var temporizador = null;

        function oculto() {
            return nomes[0] ? document[nomes[0]] : false;
        }

        function parar() {
            if (temporizador) {
                clearInterval(temporizador);
                temporizador = null;
            }
        }

        function iniciar() {
            parar();
            temporizador = setInterval(funcao, segundos * 1000);
        }

        if (nomes[1]) {
            document.addEventListener(nomes[1], function () {
                if (oculto()) {
                    parar();
                } else {
                    funcao();
                    iniciar();
                }
            });
        }
        // Voltou para a página pelo "voltar" do navegador: atualiza na hora.
        window.addEventListener('pageshow', function (evento) {
            if (evento.persisted) {
                funcao();
            }
        });
        if (!oculto()) {
            iniciar();
        }
    }

    window.TucandeiraRede = {pedir: pedir, periodicamente: periodicamente};
}());
