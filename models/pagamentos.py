from dataclasses import dataclass, field
from typing import List, Optional

import config
from models.comandas import Conta


@dataclass
class Pagamento:
    id: int
    comanda_id: int
    caixa_id: int
    forma: str
    valor_centavos: int
    recebido_centavos: Optional[int]
    troco_centavos: int
    recebido_por: int
    criado_em: str
    estornado_em: Optional[str] = None
    estornado_por: Optional[int] = None
    estorno_autorizado_por: Optional[int] = None
    motivo_estorno: Optional[str] = None
    recebido_por_nome: Optional[str] = None

    @property
    def estornado(self):
        return self.estornado_em is not None

    @property
    def forma_nome(self):
        return config.FORMAS_PAGAMENTO.get(self.forma, self.forma)


@dataclass
class Desconto:
    id: int
    comanda_id: int
    valor_centavos: int
    motivo: str
    usuario_id: int
    autorizado_por: int
    criado_em: str


@dataclass
class ItemVenda:
    id: int
    venda_id: int
    produto_id: int
    nome_produto: str
    preco_unitario_centavos: int
    quantidade: int
    subtotal_centavos: int


@dataclass
class Venda:
    id: int
    comanda_id: int
    caixa_id: int
    pessoas: int
    subtotal_centavos: int
    desconto_centavos: int
    total_centavos: int
    fechada_por: int
    criado_em: str
    itens: List[ItemVenda] = field(default_factory=list)


@dataclass
class ResultadoPagamento:
    """O que a tela precisa mostrar depois de um pagamento ou desconto."""
    conta: Conta
    pagamento: Optional[Pagamento] = None
    venda: Optional[Venda] = None
    avisos_estoque: List[str] = field(default_factory=list)

    @property
    def quitada(self):
        return self.venda is not None
