"""Relatórios por período: vendas, formas de pagamento, produtos mais vendidos,
cancelamentos, descontos, estoque e fechamentos de caixa. Também gera o CSV.

Regras:
- O período é por dia de operação: cada venda, cancelamento, desconto, estorno e
  fechamento conta no dia em que o caixa dele foi aberto (uma venda à 01:00 entra
  na noite anterior). Inclui o dia inicial e o final. Nunca é o total geral.
- "Hoje" é a noite do caixa aberto (ou do último fechado, se não houver caixa aberto).
  "Esta semana" (segunda até hoje) e "Este mês" (dia 1º até hoje) seguem o calendário.
- O total por forma soma os pagamentos não estornados das vendas do período;
  assim, a soma das formas é sempre igual ao total vendido.
- Comandas abertas ou canceladas não entram nas vendas.
- Cancelamentos: itens cancelados (com PIN do gerente), comandas canceladas com
  itens e estornos. Remoção dentro do prazo (sem PIN) não é cancelamento.
"""
import csv
import io
from datetime import date, datetime, timedelta

import config
from models.caixa import ConferenciaForma
from models.relatorios import FechamentoCaixa, Ocorrencia, Periodo, ProdutoVendido, ResumoVendas
from services import caixa as servico_caixa
from services import comandas, produtos
from services.erros import DadosInvalidosError, NaoEncontradoError

FORMAS = config.FORMAS_PAGAMENTO
MAXIMO_DIAS = 366
FORMATO_DATA = "%Y-%m-%d"


# ============================================================
# PERÍODO
# ============================================================
def periodo(tipo, hoje=None, de=None, ate=None, dia_operacao=None):
    """Monta o período: 'dia' (o dia de operação), 'semana' (de segunda até hoje), 'mes'
    (do dia 1 até hoje) ou 'intervalo' (de/até digitados, no formato AAAA-MM-DD do seletor
    de data). `hoje` é a data do calendário; `dia_operacao`, a de dia_de_operacao()."""
    hoje = hoje or date.today()
    if tipo == "dia":
        dia = dia_operacao or hoje
        return Periodo(dia, dia, tipo)
    if tipo == "semana":
        return Periodo(hoje - timedelta(days=hoje.weekday()), hoje, tipo)
    if tipo == "mes":
        return Periodo(hoje.replace(day=1), hoje, tipo)
    if tipo != "intervalo":
        raise DadosInvalidosError("Período inválido.")
    inicio, fim = _ler_data(de, "a data inicial"), _ler_data(ate, "a data final")
    if fim < inicio:
        raise DadosInvalidosError("A data final é antes da data inicial.")
    if (fim - inicio).days >= MAXIMO_DIAS:
        raise DadosInvalidosError(f"Escolha um intervalo de até {MAXIMO_DIAS} dias.")
    return Periodo(inicio, fim, tipo)


def dia_de_operacao(conexao, hoje=None):
    """Data de abertura do caixa aberto; sem caixa aberto, a do último fechado; sem nenhum, hoje."""
    atual = servico_caixa.caixa_aberto(conexao) or servico_caixa.ultimo_fechado(conexao)
    if atual is None:
        return hoje or date.today()
    return datetime.strptime(atual.aberto_em, "%Y-%m-%d %H:%M:%S").date()


def _ler_data(texto, campo):
    try:
        return datetime.strptime((texto or "").strip(), FORMATO_DATA).date()
    except ValueError:
        raise DadosInvalidosError(f"Informe {campo}.") from None


def _limites(p):
    """Início e fim (exclusivo) no formato do banco, para `cx.aberto_em >= ? AND cx.aberto_em < ?`."""
    return f"{p.inicio:%Y-%m-%d} 00:00:00", f"{p.fim + timedelta(days=1):%Y-%m-%d} 00:00:00"


def nome_periodo(p):
    """'Hoje, 15/10/2026', 'Semana: 12/10/2026 a 15/10/2026'..."""
    if p.inicio == p.fim:
        prefixo = "Hoje, " if p.tipo == "dia" else ""
        return f"{prefixo}{p.inicio:%d/%m/%Y}"
    prefixo = {"semana": "Semana: ", "mes": "Mês: "}.get(p.tipo, "")
    return f"{prefixo}{p.inicio:%d/%m/%Y} a {p.fim:%d/%m/%Y}"


# ============================================================
# VENDAS
# ============================================================
def resumo_vendas(conexao, p):
    inicio, fim = _limites(p)
    linha = conexao.execute(
        """SELECT COUNT(*) AS numero, COALESCE(SUM(subtotal_centavos), 0) AS subtotal,
                  COALESCE(SUM(desconto_centavos), 0) AS desconto, COALESCE(SUM(total_centavos), 0) AS total
           FROM vendas v JOIN caixas cx ON cx.id = v.caixa_id
           WHERE cx.aberto_em >= ? AND cx.aberto_em < ?""",
        (inicio, fim),
    ).fetchone()
    por_forma = {forma: 0 for forma in FORMAS}
    for forma, valor in conexao.execute(
            """SELECT p.forma, SUM(p.valor_centavos) FROM pagamentos p
               JOIN vendas v ON v.comanda_id = p.comanda_id
               JOIN caixas cx ON cx.id = v.caixa_id
               WHERE cx.aberto_em >= ? AND cx.aberto_em < ? AND p.estornado_em IS NULL
               GROUP BY p.forma""",
            (inicio, fim)).fetchall():
        por_forma[forma] = valor
    return ResumoVendas(linha["numero"], linha["subtotal"], linha["desconto"], linha["total"], por_forma)


def produtos_mais_vendidos(conexao, p, limite=30):
    inicio, fim = _limites(p)
    linhas = conexao.execute(
        """SELECT iv.produto_id, SUM(iv.quantidade) AS quantidade, SUM(iv.subtotal_centavos) AS total,
                  (SELECT iv2.nome_produto FROM itens_venda iv2 WHERE iv2.produto_id = iv.produto_id
                   ORDER BY iv2.id DESC LIMIT 1) AS nome
           FROM itens_venda iv JOIN vendas v ON v.id = iv.venda_id
           JOIN caixas cx ON cx.id = v.caixa_id
           WHERE cx.aberto_em >= ? AND cx.aberto_em < ?
           GROUP BY iv.produto_id ORDER BY quantidade DESC, total DESC, nome LIMIT ?""",
        (inicio, fim, limite),
    ).fetchall()
    return [ProdutoVendido(l["produto_id"], l["nome"], l["quantidade"], l["total"]) for l in linhas]


# ============================================================
# CANCELAMENTOS, ESTORNOS E DESCONTOS
# ============================================================
def _identificacoes(conexao):
    """Guarda a identificação de cada comanda ('Mesa 3', 'Balcão — João') já consultada."""
    cache = {}

    def identificar(comanda_id):
        if comanda_id not in cache:
            try:
                cache[comanda_id] = comandas.obter_comanda(conexao, comanda_id).identificacao
            except NaoEncontradoError:
                cache[comanda_id] = f"Comanda {comanda_id}"
        return cache[comanda_id]
    return identificar


def cancelamentos(conexao, p):
    """Itens cancelados, comandas canceladas com itens e estornos, do mais recente ao mais antigo.

    Os itens cancelados junto com a comanda inteira aparecem numa linha só
    ("Comanda cancelada", com o valor de todos eles), para não contar duas vezes.
    """
    inicio, fim = _limites(p)
    identificar = _identificacoes(conexao)
    resultado, por_comanda = [], {}
    for l in conexao.execute(
            """SELECT a.criado_em, a.quantidade, a.motivo, i.nome_produto, i.preco_unitario_centavos,
                      i.comanda_id, c.status, c.fechada_em, c.cancelamento_autorizado_por,
                      u.nome AS usuario_nome, g.nome AS autorizado_por_nome
               FROM item_ajustes a
               JOIN itens_comanda i ON i.id = a.item_id
               JOIN comandas c ON c.id = i.comanda_id
               JOIN caixas cx ON cx.id = c.caixa_id
               JOIN usuarios u ON u.id = a.usuario_id
               LEFT JOIN usuarios g ON g.id = a.autorizado_por
               WHERE a.tipo = 'cancelamento' AND cx.aberto_em >= ? AND cx.aberto_em < ?
               ORDER BY a.criado_em, a.id""",
            (inicio, fim)).fetchall():
        valor = l["quantidade"] * l["preco_unitario_centavos"]
        da_comanda_inteira = (l["status"] == "cancelada" and l["criado_em"] == l["fechada_em"]
                              and l["cancelamento_autorizado_por"] is not None)
        if da_comanda_inteira:
            ocorrencia = por_comanda.get(l["comanda_id"])
            if ocorrencia is None:
                ocorrencia = Ocorrencia(l["criado_em"], "comanda_cancelada", identificar(l["comanda_id"]), "", 0,
                                        l["motivo"], l["usuario_nome"], l["autorizado_por_nome"])
                por_comanda[l["comanda_id"]] = ocorrencia
                resultado.append(ocorrencia)
            ocorrencia.valor_centavos += valor
            ocorrencia.descricao = ", ".join(filter(None, [ocorrencia.descricao,
                                                           f"{l['quantidade']}× {l['nome_produto']}"]))
        else:
            resultado.append(Ocorrencia(l["criado_em"], "item_cancelado", identificar(l["comanda_id"]),
                                        f"{l['quantidade']}× {l['nome_produto']}", valor, l["motivo"],
                                        l["usuario_nome"], l["autorizado_por_nome"]))
    for l in conexao.execute(
            """SELECT p.estornado_em, p.forma, p.valor_centavos, p.motivo_estorno, p.comanda_id,
                      u.nome AS usuario_nome, g.nome AS autorizado_por_nome
               FROM pagamentos p
               JOIN caixas cx ON cx.id = p.caixa_id
               JOIN usuarios u ON u.id = p.estornado_por
               LEFT JOIN usuarios g ON g.id = p.estorno_autorizado_por
               WHERE p.estornado_em IS NOT NULL AND cx.aberto_em >= ? AND cx.aberto_em < ?""",
            (inicio, fim)).fetchall():
        resultado.append(Ocorrencia(l["estornado_em"], "estorno", identificar(l["comanda_id"]),
                                    f"Pagamento em {FORMAS.get(l['forma'], l['forma'])}", l["valor_centavos"],
                                    l["motivo_estorno"], l["usuario_nome"], l["autorizado_por_nome"]))
    resultado.sort(key=lambda o: o.criado_em, reverse=True)
    return resultado


def descontos(conexao, p):
    """Descontos lançados no período (com quem lançou e o gerente que autorizou)."""
    inicio, fim = _limites(p)
    identificar = _identificacoes(conexao)
    return [
        Ocorrencia(l["criado_em"], "desconto", identificar(l["comanda_id"]),
                   "" if l["status"] == "paga" else "Comanda ainda não paga", l["valor_centavos"], l["motivo"],
                   l["usuario_nome"], l["autorizado_por_nome"])
        for l in conexao.execute(
            """SELECT d.*, c.status, u.nome AS usuario_nome, g.nome AS autorizado_por_nome
               FROM descontos d
               JOIN comandas c ON c.id = d.comanda_id
               JOIN caixas cx ON cx.id = c.caixa_id
               JOIN usuarios u ON u.id = d.usuario_id
               JOIN usuarios g ON g.id = d.autorizado_por
               WHERE cx.aberto_em >= ? AND cx.aberto_em < ?
               ORDER BY d.criado_em DESC, d.id DESC""",
            (inicio, fim)).fetchall()
    ]


# ============================================================
# ESTOQUE E CAIXA
# ============================================================
def estoque_em_alerta(conexao):
    """Produtos ativos com estoque negativo, zerado ou abaixo do mínimo (situação de agora)."""
    ordem = {"negativo": 0, "zerado": 1, "abaixo_minimo": 2}
    return sorted(produtos.listar_alertas_estoque(conexao), key=lambda p: (ordem[p.situacao_estoque], p.nome))


def fechamentos_caixa(conexao, p):
    """Caixas fechados abertos no período, com a conferência por forma e as diferenças."""
    inicio, fim = _limites(p)
    caixas = conexao.execute(
        """SELECT c.id, c.aberto_em, c.fechado_em, a.nome AS aberto_por_nome, f.nome AS fechado_por_nome
           FROM caixas c
           JOIN usuarios a ON a.id = c.aberto_por
           JOIN usuarios f ON f.id = c.fechado_por
           WHERE c.status = 'fechado' AND c.aberto_em >= ? AND c.aberto_em < ?
           ORDER BY c.fechado_em DESC""",
        (inicio, fim),
    ).fetchall()
    resultado = []
    for c in caixas:
        conferencias = [
            ConferenciaForma(l["forma"], l["esperado_centavos"], l["contado_centavos"])
            for l in conexao.execute("SELECT * FROM caixa_conferencias WHERE caixa_id = ?", (c["id"],)).fetchall()
        ]
        conferencias.sort(key=lambda conf: list(FORMAS).index(conf.forma))
        resultado.append(FechamentoCaixa(c["id"], c["aberto_em"], c["fechado_em"], c["aberto_por_nome"],
                                         c["fechado_por_nome"], conferencias))
    return resultado


# ============================================================
# CSV (separador ";" e UTF-8 com BOM, para abrir certo no Excel)
# ============================================================
RELATORIOS_CSV = ("vendas", "produtos", "cancelamentos", "descontos", "estoque", "caixas")


def _reais(centavos):
    """Valor para o Excel em português: '1234,56' (sem 'R$', vírgula decimal)."""
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    return f"{sinal}{reais},{resto:02d}"


def _data_hora(texto):
    return datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M") if texto else ""


def linhas_csv(conexao, relatorio, p):
    """Cabeçalho + linhas de um relatório, prontos para o CSV."""
    if relatorio == "vendas":
        r = resumo_vendas(conexao, p)
        linhas = [["Período", nome_periodo(p)], ["Número de vendas", r.numero_vendas],
                  ["Subtotal (R$)", _reais(r.subtotal_centavos)], ["Descontos (R$)", _reais(r.desconto_centavos)],
                  ["Total vendido (R$)", _reais(r.total_centavos)], ["Ticket médio (R$)", _reais(r.ticket_medio_centavos)]]
        linhas += [[f"{nome} (R$)", _reais(r.por_forma[forma])] for forma, nome in FORMAS.items()]
        return [["Item", "Valor"]] + linhas
    if relatorio == "produtos":
        return [["Produto", "Quantidade", "Total (R$)"]] + [
            [v.nome, v.quantidade, _reais(v.total_centavos)] for v in produtos_mais_vendidos(conexao, p, limite=1000)]
    if relatorio in ("cancelamentos", "descontos"):
        lista = cancelamentos(conexao, p) if relatorio == "cancelamentos" else descontos(conexao, p)
        return [["Data", "Tipo", "Comanda", "Descrição", "Valor (R$)", "Motivo", "Lançado por", "Autorizado por"]] + [
            [_data_hora(o.criado_em), o.tipo_nome, o.comanda, o.descricao, _reais(o.valor_centavos), o.motivo,
             o.usuario_nome, o.autorizado_por_nome or ""] for o in lista]
    if relatorio == "estoque":
        situacoes = {"negativo": "Estoque negativo", "zerado": "Sem estoque", "abaixo_minimo": "Abaixo do mínimo"}
        return [["Produto", "Categoria", "Estoque", "Mínimo", "Situação"]] + [
            [x.nome, x.categoria_nome, x.estoque, x.estoque_minimo, situacoes[x.situacao_estoque]]
            for x in estoque_em_alerta(conexao)]
    if relatorio == "caixas":
        cabecalho = ["Caixa", "Aberto em", "Fechado em", "Aberto por", "Fechado por"]
        for nome in FORMAS.values():
            cabecalho += [f"{nome} esperado (R$)", f"{nome} contado (R$)", f"{nome} diferença (R$)"]
        linhas = [cabecalho + ["Diferença total (R$)"]]
        for f in fechamentos_caixa(conexao, p):
            linha = [f.caixa_id, _data_hora(f.aberto_em), _data_hora(f.fechado_em), f.aberto_por_nome,
                     f.fechado_por_nome]
            por_forma = {c.forma: c for c in f.conferencias}
            for forma in FORMAS:
                c = por_forma.get(forma)
                linha += ([_reais(c.esperado_centavos), _reais(c.contado_centavos), _reais(c.diferenca_centavos)]
                          if c else ["", "", ""])
            linhas.append(linha + [_reais(f.diferenca_total_centavos)])
        return linhas
    raise DadosInvalidosError("Relatório inválido.")


def gerar_csv(linhas):
    """Texto do CSV: UTF-8 com BOM (acentos certos no Excel) e separador ';'."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerows(linhas)
    return "﻿" + saida.getvalue()


def nome_arquivo_csv(relatorio, p):
    return f"tucandeira_{relatorio}_{p.inicio:%Y-%m-%d}_a_{p.fim:%Y-%m-%d}.csv"
