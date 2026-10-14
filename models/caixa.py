from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Caixa:
    id: int
    status: str
    valor_inicial_centavos: int
    aberto_em: str
    aberto_por: int
    fechado_em: Optional[str] = None
    fechado_por: Optional[int] = None
    observacao: Optional[str] = None

    @property
    def aberto(self):
        return self.status == "aberto"


@dataclass
class CaixaMovimento:
    id: int
    caixa_id: int
    tipo: str
    valor_centavos: int
    motivo: str
    usuario_id: int
    autorizado_por: Optional[int]
    criado_em: str
    usuario_nome: Optional[str] = None


@dataclass
class ConferenciaForma:
    forma: str
    esperado_centavos: int
    contado_centavos: int

    @property
    def diferenca_centavos(self):
        """Positivo = sobrou dinheiro; negativo = faltou."""
        return self.contado_centavos - self.esperado_centavos


@dataclass
class ResultadoFechamento:
    caixa: Caixa
    conferencias: List[ConferenciaForma] = field(default_factory=list)

    @property
    def diferenca_total_centavos(self):
        return sum(c.diferenca_centavos for c in self.conferencias)
