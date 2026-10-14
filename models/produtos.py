from dataclasses import dataclass
from typing import Optional

TIPOS_MOVIMENTO = {"entrada": "Entrada", "perda": "Perda", "ajuste": "Ajuste de contagem"}


@dataclass
class Categoria:
    id: int
    nome: str
    ordem: int
    ativo: bool


@dataclass
class Produto:
    id: int
    nome: str
    categoria_id: int
    preco_centavos: int
    estoque: int
    estoque_minimo: int
    ativo: bool
    criado_em: str
    atualizado_em: str
    categoria_nome: Optional[str] = None

    @property
    def situacao_estoque(self):
        """'negativo', 'zerado', 'abaixo_minimo' ou 'ok'."""
        if self.estoque < 0:
            return "negativo"
        if self.estoque == 0:
            return "zerado"
        if self.estoque < self.estoque_minimo:
            return "abaixo_minimo"
        return "ok"

    @property
    def precisa_atencao(self):
        return self.situacao_estoque != "ok"


@dataclass
class MovimentoEstoque:
    id: int
    produto_id: int
    tipo: str
    quantidade: int
    estoque_contado: Optional[int]
    custo_unitario_centavos: Optional[int]
    motivo: Optional[str]
    usuario_id: int
    autorizado_por: Optional[int]
    criado_em: str
    usuario_nome: Optional[str] = None
    autorizado_por_nome: Optional[str] = None

    @property
    def tipo_nome(self):
        return TIPOS_MOVIMENTO.get(self.tipo, self.tipo)
