from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LinhaImportacao:
    """Uma linha da planilha do cardápio, já conferida contra o banco.

    `acao`: 'novo' (produto a cadastrar), 'alterar' (produto existente que muda),
    'igual' (nada muda) ou 'erro' (a linha tem problemas e impede a importação).
    `estoque` e `estoque_minimo` são None quando a célula ficou em branco.
    """
    numero: int
    categoria: str
    produto: str
    preco_centavos: Optional[int] = None
    estoque: Optional[int] = None
    estoque_minimo: Optional[int] = None
    acao: str = "erro"
    mudancas: List[str] = field(default_factory=list)
    erros: List[str] = field(default_factory=list)
    produto_id: Optional[int] = None


@dataclass
class ConferenciaImportacao:
    """Resultado da conferência da planilha, mostrado antes de gravar."""
    linhas: List[LinhaImportacao] = field(default_factory=list)
    erros_gerais: List[str] = field(default_factory=list)
    categorias_novas: List[str] = field(default_factory=list)
    categorias_reativadas: List[str] = field(default_factory=list)
    ausentes: List[str] = field(default_factory=list)  # produtos ativos que não estão na planilha

    def _contar(self, acao):
        return sum(1 for linha in self.linhas if linha.acao == acao)

    @property
    def novos(self):
        return self._contar("novo")

    @property
    def alterados(self):
        return self._contar("alterar")

    @property
    def iguais(self):
        return self._contar("igual")

    @property
    def com_erro(self):
        return self._contar("erro")

    @property
    def tem_erros(self):
        return bool(self.erros_gerais) or self.com_erro > 0

    @property
    def tem_mudancas(self):
        return bool(self.novos or self.alterados or self.categorias_novas or self.categorias_reativadas)


@dataclass
class ResultadoImportacao:
    novos: int
    alterados: int
    categorias_novas: int
    desativados: int
