from dataclasses import fields


def de_linha(classe, linha, **extras):
    """Cria uma dataclass a partir de uma linha do banco (sqlite3.Row).

    Colunas que não existem na classe são ignoradas; `extras` completa ou
    substitui campos.
    """
    nomes = {campo.name for campo in fields(classe)}
    dados = {chave: linha[chave] for chave in linha.keys() if chave in nomes}
    dados.update(extras)
    return classe(**dados)
