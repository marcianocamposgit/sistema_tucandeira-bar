"""Exceções de regra de negócio.

Os services lançam estas exceções; as rotas decidem como mostrar ao usuário.
A mensagem (str(erro)) já vem pronta para exibir, em português.
"""


class ErroDeNegocio(Exception):
    """Base de todos os erros previstos pelas regras do bar."""


class DadosInvalidosError(ErroDeNegocio):
    """Valor fora do permitido (preço negativo, PIN com letras, campo vazio...)."""


class NaoEncontradoError(ErroDeNegocio):
    pass


class NomeDuplicadoError(DadosInvalidosError):
    pass


class PinInvalidoError(ErroDeNegocio):
    """Usuário ou PIN incorretos. A mensagem é sempre genérica de propósito."""

    def __init__(self, mensagem="PIN incorreto."):
        super().__init__(mensagem)


class PermissaoNegadaError(ErroDeNegocio):
    """Ação exige gerente e a autorização não foi dada ou não confere."""

    def __init__(self, mensagem="Esta ação precisa da autorização de um gerente."):
        super().__init__(mensagem)


class UltimoGerenteError(ErroDeNegocio):
    def __init__(self, mensagem="É preciso manter pelo menos um gerente ativo."):
        super().__init__(mensagem)


class CaixaFechadoError(ErroDeNegocio):
    def __init__(self, mensagem="O caixa está fechado. Abra o caixa para continuar."):
        super().__init__(mensagem)


class CaixaJaAbertoError(ErroDeNegocio):
    def __init__(self, mensagem="Já existe um caixa aberto."):
        super().__init__(mensagem)


class ComandasAbertasError(ErroDeNegocio):
    """O caixa não fecha enquanto houver comandas abertas ou com conta pedida."""

    def __init__(self, comandas):
        self.comandas = list(comandas)
        nomes = ", ".join(c.identificacao for c in self.comandas)
        super().__init__(f"Não é possível fechar o caixa: há comandas pendentes ({nomes}).")


class MesaOcupadaError(ErroDeNegocio):
    def __init__(self, mesa):
        self.mesa = mesa
        super().__init__(f"A mesa {mesa} já está ocupada.")


class ComandaFechadaError(ErroDeNegocio):
    """A comanda já foi paga, cancelada ou juntada a outra (talvez em outro aparelho)."""

    def __init__(self, mensagem="Esta comanda já foi fechada. Atualize a tela."):
        super().__init__(mensagem)


class PrazoRemocaoExpiradoError(ErroDeNegocio):
    def __init__(self, minutos):
        super().__init__(
            f"Passou o prazo de {minutos} minuto(s) para remover este item. "
            "Use o cancelamento (motivo e PIN do gerente)."
        )


class ComandaComPagamentosError(ErroDeNegocio):
    def __init__(self, mensagem="Esta comanda já tem pagamentos. Estorne-os antes de cancelar."):
        super().__init__(mensagem)


class TotalAbaixoDoPagoError(ErroDeNegocio):
    def __init__(self, mensagem="A conta ficaria menor que o valor já pago. Estorne um pagamento antes."):
        super().__init__(mensagem)
