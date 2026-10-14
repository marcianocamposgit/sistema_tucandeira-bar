from dataclasses import dataclass, field
from typing import Optional

PERFIS = {"operador": "Operador", "gerente": "Gerente"}


@dataclass
class Usuario:
    id: int
    nome: str
    perfil: str
    ativo: bool
    criado_em: str
    criado_por: Optional[int] = None

    @property
    def gerente(self):
        return self.perfil == "gerente"

    @property
    def perfil_nome(self):
        return PERFIS.get(self.perfil, self.perfil)


@dataclass(frozen=True)
class AutorizacaoGerente:
    """Gerente escolhido na lista + PIN digitado na hora, para uma única ação."""
    gerente_id: int
    pin: str = field(repr=False)
