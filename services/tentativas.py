"""Bloqueio temporário após PINs errados seguidos.

Fica em memória (zera se o servidor reiniciar). Cada erro conta para todas as
chaves informadas — ex.: ("usuario", 3) e ("aparelho", "192.168.0.20") —, e a
tentativa fica bloqueada se qualquer uma delas estiver bloqueada.
"""
import threading
import time


class ControleTentativas:
    def __init__(self, maximo, bloqueio_segundos, relogio=time.monotonic):
        self.maximo = maximo
        self.bloqueio_segundos = bloqueio_segundos
        self._relogio = relogio
        self._erros = {}          # chave -> erros seguidos
        self._bloqueado_ate = {}  # chave -> instante (relógio) em que o bloqueio acaba
        self._trava = threading.Lock()

    def segundos_bloqueado(self, chaves):
        """0 se pode tentar; senão, quantos segundos faltam para liberar."""
        agora = self._relogio()
        with self._trava:
            restantes = [self._bloqueado_ate.get(c, 0) - agora for c in chaves]
        return max(0, int(max(restantes, default=0) + 0.999))

    def registrar_erro(self, chaves):
        agora = self._relogio()
        with self._trava:
            for chave in chaves:
                if self._bloqueado_ate.get(chave, 0) <= agora and chave in self._bloqueado_ate:
                    # Bloqueio anterior já acabou: recomeça a contagem.
                    del self._bloqueado_ate[chave]
                    self._erros[chave] = 0
                self._erros[chave] = self._erros.get(chave, 0) + 1
                if self._erros[chave] >= self.maximo:
                    self._bloqueado_ate[chave] = agora + self.bloqueio_segundos
                    self._erros[chave] = 0

    def registrar_acerto(self, chaves):
        with self._trava:
            for chave in chaves:
                self._erros.pop(chave, None)
                self._bloqueado_ate.pop(chave, None)
