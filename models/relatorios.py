from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from models.caixa import ConferenciaForma


@dataclass
class Periodo:
    """Intervalo de datas de um relatório (inclui o dia inicial e o final)."""
    inicio: date
    fim: date
    tipo: str  # 'dia', 'semana', 'mes' ou 'intervalo'


@dataclass
class ResumoVendas:
    """Vendas fechadas no período. `por_forma` soma os pagamentos não estornados dessas vendas."""
    numero_vendas: int
    subtotal_centavos: int
    desconto_centavos: int
    total_centavos: int
    por_forma: Dict[str, int] = field(default_factory=dict)

    @property
    def ticket_medio_centavos(self):
        """Total dividido pelo número de vendas (arredondado para baixo no centavo)."""
        return self.total_centavos // self.numero_vendas if self.numero_vendas else 0


@dataclass
class ProdutoVendido:
    produto_id: int
    nome: str
    quantidade: int
    total_centavos: int


@dataclass
class Ocorrencia:
    """Cancelamento de item, comanda cancelada, estorno de pagamento ou desconto."""
    criado_em: str
    tipo: str  # 'item_cancelado', 'comanda_cancelada', 'estorno' ou 'desconto'
    comanda: str
    descricao: str
    valor_centavos: int
    motivo: str
    usuario_nome: str
    autorizado_por_nome: Optional[str] = None

    @property
    def tipo_nome(self):
        return {"item_cancelado": "Item cancelado", "comanda_cancelada": "Comanda cancelada",
                "estorno": "Estorno de pagamento", "desconto": "Desconto"}.get(self.tipo, self.tipo)


@dataclass
class FechamentoCaixa:
    caixa_id: int
    aberto_em: str
    fechado_em: str
    aberto_por_nome: str
    fechado_por_nome: str
    conferencias: List[ConferenciaForma] = field(default_factory=list)

    @property
    def diferenca_total_centavos(self):
        return sum(c.diferenca_centavos for c in self.conferencias)
