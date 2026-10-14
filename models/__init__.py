"""Classes de dados do sistema (dataclasses), sem regra de negócio.

Os services devolvem estes objetos para as rotas e templates.
"""
from models.base import de_linha
from models.caixa import Caixa, CaixaMovimento, ConferenciaForma, ResultadoFechamento
from models.comandas import (
    Comanda,
    ComandaPendente,
    Conta,
    EstadoMesa,
    ItemComanda,
    ResultadoLancamento,
    ResumoComanda,
)
from models.pagamentos import Desconto, ItemVenda, Pagamento, ResultadoPagamento, Venda
from models.produtos import Categoria, MovimentoEstoque, Produto
from models.usuarios import AutorizacaoGerente, Usuario

__all__ = [
    "AutorizacaoGerente", "Caixa", "CaixaMovimento", "Categoria", "Comanda", "ComandaPendente",
    "ConferenciaForma", "Conta", "Desconto", "EstadoMesa", "ItemComanda", "ItemVenda", "MovimentoEstoque",
    "Pagamento", "Produto", "ResultadoFechamento", "ResultadoLancamento", "ResultadoPagamento",
    "ResumoComanda", "Usuario", "Venda", "de_linha",
]
