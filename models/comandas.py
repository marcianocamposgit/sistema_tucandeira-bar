from dataclasses import dataclass, field
from typing import List, Optional

STATUS_COMANDA = {
    "aberta": "Aberta",
    "conta_pedida": "Conta pedida",
    "paga": "Paga",
    "unida": "Unida a outra",
    "cancelada": "Cancelada",
}
STATUS_EDITAVEIS = ("aberta", "conta_pedida")


@dataclass
class Comanda:
    id: int
    tipo: str
    nome_cliente: Optional[str]
    pessoas: int
    status: str
    caixa_id: int
    unida_a: Optional[int]
    taxa_servico_ativa: bool
    taxa_removida_por: Optional[int]
    couvert_unitario_centavos: int
    aberta_em: str
    aberta_por: int
    fechada_em: Optional[str] = None
    fechada_por: Optional[int] = None
    motivo_cancelamento: Optional[str] = None
    cancelamento_autorizado_por: Optional[int] = None
    mesas: List[int] = field(default_factory=list)

    @property
    def editavel(self):
        return self.status in STATUS_EDITAVEIS

    @property
    def identificacao(self):
        """'Mesa 3', 'Mesas 3 + 4' ou 'Balcão — João'."""
        if self.tipo == "balcao":
            return f"Balcão — {self.nome_cliente}"
        if len(self.mesas) > 1:
            return "Mesas " + " + ".join(str(m) for m in self.mesas)
        if self.mesas:
            return f"Mesa {self.mesas[0]}"
        return f"Comanda {self.id}"


@dataclass
class ItemComanda:
    id: int
    comanda_id: int
    produto_id: int
    nome_produto: str
    preco_unitario_centavos: int
    quantidade: int
    observacao: Optional[str]
    lancado_por: int
    lancado_em: str
    lancado_por_nome: Optional[str] = None

    @property
    def subtotal_centavos(self):
        return self.preco_unitario_centavos * self.quantidade


@dataclass
class Conta:
    """Valores da comanda, sempre recalculados a partir dos itens atuais."""
    subtotal_centavos: int
    taxa_servico_centavos: int
    couvert_centavos: int
    desconto_centavos: int
    pago_centavos: int
    pessoas: int

    @property
    def total_centavos(self):
        return max(0, self.subtotal_centavos + self.taxa_servico_centavos
                   + self.couvert_centavos - self.desconto_centavos)

    @property
    def saldo_centavos(self):
        return self.total_centavos - self.pago_centavos

    @property
    def por_pessoa_centavos(self):
        """Total dividido igualmente (arredondado para cima no centavo)."""
        return -(-self.total_centavos // max(1, self.pessoas))


@dataclass
class ResumoComanda:
    comanda: Comanda
    conta: Conta
    itens: List[ItemComanda] = field(default_factory=list)


@dataclass
class EstadoMesa:
    numero: int
    status: str  # 'livre', 'ocupada' ou 'conta_pedida'
    comanda_id: Optional[int] = None
    pessoas: int = 0
    total_centavos: int = 0
    mesas_juntas: List[int] = field(default_factory=list)


@dataclass
class ComandaPendente:
    """Comanda que impede o fechamento do caixa."""
    comanda_id: int
    identificacao: str
    status: str
    total_centavos: int
    saldo_centavos: int


@dataclass
class ResultadoLancamento:
    item: ItemComanda
    aviso_estoque: Optional[str] = None
