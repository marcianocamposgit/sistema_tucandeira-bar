import threading
from datetime import datetime, timedelta

import pytest

import config
from database import conectar
from models import AutorizacaoGerente
from services import caixa, comandas
from services.erros import (
    CaixaFechadoError,
    ComandaComPagamentosError,
    ComandaFechadaError,
    DadosInvalidosError,
    MesaOcupadaError,
    NaoEncontradoError,
    PermissaoNegadaError,
    PrazoRemocaoExpiradoError,
    TotalAbaixoDoPagoError,
)
from tests.auxiliares import fechar_comanda_como_paga, inserir_pagamento

BRAHMA, HEINEKEN, WHISKY, CALABRESA, PASTEL, MARLBORO = 1, 2, 3, 4, 5, 6


def test_abrir_comanda_exige_caixa_aberto(conexao, operador):
    with pytest.raises(CaixaFechadoError):
        comandas.abrir_mesa(conexao, 1, operador.id)
    with pytest.raises(CaixaFechadoError):
        comandas.abrir_balcao(conexao, "João", operador.id)


def test_abrir_mesa(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 3, operador.id, pessoas=4)
    assert (c.tipo, c.mesas, c.pessoas, c.identificacao) == ("mesa", [3], 4, "Mesa 3")
    with pytest.raises(MesaOcupadaError):
        comandas.abrir_mesa(conexao, 3, operador.id)
    with pytest.raises(DadosInvalidosError):
        comandas.abrir_mesa(conexao, config.NUM_MESAS + 1, operador.id)
    with pytest.raises(DadosInvalidosError):
        comandas.abrir_mesa(conexao, 4, operador.id, pessoas=0)


def test_balcao_varias_comandas_por_nome(conexao, operador, caixa_aberto):
    joao = comandas.abrir_balcao(conexao, "João", operador.id)
    maria = comandas.abrir_balcao(conexao, "Maria", operador.id)
    assert joao.identificacao == "Balcão — João"
    with pytest.raises(DadosInvalidosError):
        comandas.abrir_balcao(conexao, "joão", operador.id)
    assert [r.comanda.id for r in comandas.listar_abertas(conexao, tipo="balcao")] == [joao.id, maria.id]


def test_lancar_itens_e_conta(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id, pessoas=2)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id, quantidade=3)
    comandas.lancar_item(conexao, c.id, CALABRESA, operador.id, observacao="  bem passada ")
    conta = comandas.calcular_conta(conexao, c.id)
    # Preço de tabela, sem acréscimos: 3 x 8,00 + 28,00 = 52,00
    assert (conta.subtotal_centavos, conta.total_centavos, conta.saldo_centavos) == (5200, 5200, 5200)
    assert conta.por_pessoa_centavos == 2600
    itens = comandas.listar_itens(conexao, c.id)
    assert [(i.nome_produto, i.quantidade, i.observacao) for i in itens] == [
        ("Brahma Lata", 3, None), ("Porção Calabresa", 1, "bem passada")]
    assert itens[0].lancado_por_nome == "Operador"


def test_preco_copiado_no_lancamento(conexao, gerente, operador, autorizacao, caixa_aberto):
    from services import produtos
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)
    produtos.editar_produto(conexao, BRAHMA, "Brahma Lata", 1, 1000, 0, gerente.id, autorizacao)
    assert comandas.listar_itens(conexao, c.id)[0].preco_unitario_centavos == 800


def test_produto_sem_estoque_avisa_e_permite(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    assert comandas.lancar_item(conexao, c.id, CALABRESA, operador.id, quantidade=8).aviso_estoque is None
    resultado = comandas.lancar_item(conexao, c.id, CALABRESA, operador.id)
    assert "sem estoque" in resultado.aviso_estoque
    assert comandas.calcular_conta(conexao, c.id).subtotal_centavos == 9 * 2800


def test_produto_desativado_nao_pode_ser_lancado(conexao, gerente, operador, autorizacao, caixa_aberto):
    from services import produtos
    produtos.desativar_produto(conexao, BRAHMA, gerente.id, autorizacao)
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    with pytest.raises(DadosInvalidosError):
        comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)


def test_remover_dentro_e_fora_do_prazo(conexao, operador, caixa_aberto):
    lancamento = datetime(2026, 10, 14, 21, 0, 0)
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    item = comandas.lancar_item(conexao, c.id, BRAHMA, operador.id, quantidade=3, agora=lancamento).item

    # Dentro dos 2 minutos: remove sem PIN.
    restante = comandas.remover_item(conexao, item.id, operador.id, agora=lancamento + timedelta(seconds=119))
    assert restante.quantidade == 2
    # No limite exato ainda pode.
    comandas.remover_item(conexao, item.id, operador.id, agora=lancamento + timedelta(minutes=2))
    # Depois do prazo: só por cancelamento.
    with pytest.raises(PrazoRemocaoExpiradoError):
        comandas.remover_item(conexao, item.id, operador.id, agora=lancamento + timedelta(minutes=2, seconds=1))
    ajustes = conexao.execute("SELECT tipo, quantidade, usuario_id FROM item_ajustes").fetchall()
    assert [tuple(a) for a in ajustes] == [("remocao", 1, operador.id), ("remocao", 1, operador.id)]


def test_prazo_configuravel(conexao, operador, caixa_aberto, monkeypatch):
    monkeypatch.setattr(config, "PRAZO_REMOCAO_ITEM_MINUTOS", 5)
    lancamento = datetime(2026, 10, 14, 21, 0, 0)
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    item = comandas.lancar_item(conexao, c.id, BRAHMA, operador.id, agora=lancamento).item
    comandas.remover_item(conexao, item.id, operador.id, agora=lancamento + timedelta(minutes=4))


def test_cancelar_item_com_e_sem_pin(conexao, gerente, operador, autorizacao, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    item = comandas.lancar_item(conexao, c.id, WHISKY, operador.id, quantidade=2).item
    with pytest.raises(PermissaoNegadaError):
        comandas.cancelar_item(conexao, item.id, "Cliente desistiu", operador.id, None)
    with pytest.raises(PermissaoNegadaError):
        comandas.cancelar_item(conexao, item.id, "Cliente desistiu", operador.id,
                               AutorizacaoGerente(gerente.id, "0000"))
    with pytest.raises(DadosInvalidosError):
        comandas.cancelar_item(conexao, item.id, "", operador.id, autorizacao)
    assert comandas.cancelar_item(conexao, item.id, "Cliente desistiu", operador.id, autorizacao).quantidade == 1
    ajuste = conexao.execute("SELECT * FROM item_ajustes").fetchone()
    assert (ajuste["tipo"], ajuste["motivo"], ajuste["usuario_id"], ajuste["autorizado_por"]) == (
        "cancelamento", "Cliente desistiu", operador.id, gerente.id)
    with pytest.raises(DadosInvalidosError):
        comandas.cancelar_item(conexao, item.id, "De novo", operador.id, autorizacao, quantidade=2)


def test_nao_deixa_a_conta_menor_que_o_ja_pago(conexao, operador, autorizacao, caixa_aberto):
    c = comandas.abrir_balcao(conexao, "Ana", operador.id)
    item = comandas.lancar_item(conexao, c.id, WHISKY, operador.id, quantidade=2).item
    inserir_pagamento(conexao, c.id, "pix", 2000, operador.id)
    with pytest.raises(TotalAbaixoDoPagoError):
        comandas.remover_item(conexao, item.id, operador.id)
    with pytest.raises(TotalAbaixoDoPagoError):
        comandas.cancelar_item(conexao, item.id, "Erro", operador.id, autorizacao)
    assert comandas.listar_itens(conexao, c.id)[0].quantidade == 2
    # Lançar mais itens depois de um pagamento parcial é permitido.
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)
    assert comandas.calcular_conta(conexao, c.id).saldo_centavos == 3000 + 800 - 2000


def test_conta_pedida_e_estado_das_mesas(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 2, operador.id, pessoas=3)
    comandas.lancar_item(conexao, c.id, PASTEL, operador.id, quantidade=2)
    comandas.marcar_conta_pedida(conexao, c.id, operador.id)
    comandas.abrir_mesa(conexao, 5, operador.id)
    estados = {e.numero: e for e in comandas.estado_mesas(conexao)}
    assert len(estados) == config.NUM_MESAS
    assert (estados[2].status, estados[2].pessoas, estados[2].total_centavos) == ("conta_pedida", 3, 1400)
    assert estados[5].status == "ocupada" and estados[1].status == "livre"
    comandas.marcar_conta_pedida(conexao, c.id, operador.id, pedida=False)
    assert comandas.obter_comanda(conexao, c.id).status == "aberta"


def test_alterar_pessoas_so_muda_a_divisao(conexao, operador, caixa_aberto):
    mesa = comandas.abrir_mesa(conexao, 1, operador.id, pessoas=2)
    comandas.lancar_item(conexao, mesa.id, CALABRESA, operador.id)
    comandas.alterar_pessoas(conexao, mesa.id, 3, operador.id)
    conta = comandas.calcular_conta(conexao, mesa.id)
    assert (conta.total_centavos, conta.pessoas, conta.por_pessoa_centavos) == (2800, 3, 934)


def test_transferir_mesa(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 2, operador.id)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)
    comandas.abrir_mesa(conexao, 6, operador.id)
    with pytest.raises(MesaOcupadaError):
        comandas.transferir_mesa(conexao, 2, 6, operador.id)
    with pytest.raises(NaoEncontradoError):
        comandas.transferir_mesa(conexao, 3, 4, operador.id)
    movida = comandas.transferir_mesa(conexao, 2, 5, operador.id)
    assert movida.id == c.id and movida.mesas == [5]
    assert comandas.comanda_da_mesa(conexao, 2) is None
    assert comandas.comanda_da_mesa(conexao, 5).id == c.id
    # A mesa antiga fica livre para outra comanda.
    comandas.abrir_mesa(conexao, 2, operador.id)


def test_juntar_mesa_livre(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 3, operador.id)
    juntas = comandas.juntar_mesas(conexao, 3, 4, operador.id)
    assert juntas.mesas == [3, 4] and juntas.identificacao == "Mesas 3 + 4"
    estados = {e.numero: e for e in comandas.estado_mesas(conexao)}
    assert estados[4].comanda_id == c.id and estados[4].mesas_juntas == [3, 4]


def test_juntar_duas_mesas_ocupadas(conexao, operador, caixa_aberto):
    a = comandas.abrir_mesa(conexao, 3, operador.id, pessoas=2)
    b = comandas.abrir_mesa(conexao, 4, operador.id, pessoas=3)
    comandas.lancar_item(conexao, a.id, BRAHMA, operador.id)
    comandas.lancar_item(conexao, b.id, HEINEKEN, operador.id, quantidade=2)
    inserir_pagamento(conexao, b.id, "pix", 1000, operador.id)
    juntas = comandas.juntar_mesas(conexao, 3, 4, operador.id)
    assert juntas.id == a.id and juntas.mesas == [3, 4] and juntas.pessoas == 5
    conta = comandas.calcular_conta(conexao, a.id)
    assert conta.subtotal_centavos == 800 + 2400 and conta.pago_centavos == 1000
    unida = comandas.obter_comanda(conexao, b.id)
    assert (unida.status, unida.unida_a) == ("unida", a.id)
    with pytest.raises(ComandaFechadaError):
        comandas.lancar_item(conexao, b.id, BRAHMA, operador.id)
    with pytest.raises(DadosInvalidosError):
        comandas.juntar_mesas(conexao, 3, 4, operador.id)
    # Ao pagar, todas as mesas são liberadas.
    fechar_comanda_como_paga(conexao, a.id, operador.id)
    assert all(e.status == "livre" for e in comandas.estado_mesas(conexao))


def test_cancelar_comanda_vazia_pelo_operador(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    item = comandas.lancar_item(conexao, c.id, BRAHMA, operador.id).item
    comandas.remover_item(conexao, item.id, operador.id)  # todos os itens removidos = vazia
    cancelada = comandas.cancelar_comanda(conexao, c.id, operador.id)
    assert cancelada.status == "cancelada" and cancelada.cancelamento_autorizado_por is None
    assert comandas.comanda_da_mesa(conexao, 1) is None
    with pytest.raises(ComandaFechadaError):
        comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)


def test_cancelar_comanda_com_itens_exige_gerente(conexao, gerente, operador, autorizacao, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id, quantidade=2)
    comandas.lancar_item(conexao, c.id, PASTEL, operador.id)
    with pytest.raises(PermissaoNegadaError):
        comandas.cancelar_comanda(conexao, c.id, operador.id, motivo="Cliente foi embora")
    with pytest.raises(DadosInvalidosError):
        comandas.cancelar_comanda(conexao, c.id, operador.id, autorizacao=autorizacao)
    cancelada = comandas.cancelar_comanda(conexao, c.id, operador.id, motivo="Cliente foi embora",
                                          autorizacao=autorizacao)
    assert (cancelada.motivo_cancelamento, cancelada.cancelamento_autorizado_por) == ("Cliente foi embora", gerente.id)
    # Cada item fica registrado como cancelado, para o relatório de cancelamentos.
    ajustes = conexao.execute("SELECT tipo, quantidade, motivo FROM item_ajustes ORDER BY id").fetchall()
    assert [tuple(a) for a in ajustes] == [("cancelamento", 2, "Cliente foi embora"),
                                           ("cancelamento", 1, "Cliente foi embora")]
    assert comandas.comanda_da_mesa(conexao, 1) is None


def test_cancelar_comanda_com_pagamento_e_recusado(conexao, operador, autorizacao, caixa_aberto):
    c = comandas.abrir_balcao(conexao, "Ana", operador.id)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)
    inserir_pagamento(conexao, c.id, "dinheiro", 800, operador.id)
    with pytest.raises(ComandaComPagamentosError):
        comandas.cancelar_comanda(conexao, c.id, operador.id, motivo="x", autorizacao=autorizacao)


def test_pagamento_estornado_nao_impede_cancelar(conexao, operador, autorizacao, caixa_aberto):
    c = comandas.abrir_balcao(conexao, "Ana", operador.id)
    inserir_pagamento(conexao, c.id, "pix", 800, operador.id, estornado=True)
    assert comandas.cancelar_comanda(conexao, c.id, operador.id).status == "cancelada"


def test_dois_aparelhos_lancando_na_mesma_comanda(tmp_path, monkeypatch):
    """Quatro "tablets" (conexões separadas) lançando ao mesmo tempo, sem perder nenhum item."""
    from database import migrar
    from services import usuarios
    monkeypatch.setattr(config, "ITERACOES_PIN", 1000)
    caminho = tmp_path / "concorrencia.db"
    con = conectar(caminho)
    migrar(con)
    garcom = usuarios.criar_gerente_inicial(con, "Garçom", "1234")
    caixa.abrir(con, 0, garcom.id)
    comanda_id = comandas.abrir_mesa(con, 1, garcom.id).id
    con.close()

    erros = []

    def tablet():
        c = conectar(caminho)
        try:
            for _ in range(20):
                comandas.lancar_item(c, comanda_id, BRAHMA, garcom.id)
        except Exception as erro:  # noqa: BLE001 - o teste só registra
            erros.append(erro)
        finally:
            c.close()

    threads = [threading.Thread(target=tablet) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert erros == []
    con = conectar(caminho)
    assert comandas.calcular_conta(con, comanda_id).subtotal_centavos == 80 * 800
    con.close()


def test_dois_aparelhos_abrindo_a_mesma_mesa(tmp_path, monkeypatch):
    """Só um dos aparelhos consegue abrir a mesa; o outro recebe MesaOcupadaError."""
    from database import migrar
    from services import usuarios
    monkeypatch.setattr(config, "ITERACOES_PIN", 1000)
    caminho = tmp_path / "mesa.db"
    con = conectar(caminho)
    migrar(con)
    garcom = usuarios.criar_gerente_inicial(con, "Garçom", "1234")
    caixa.abrir(con, 0, garcom.id)
    con.close()

    resultados = []
    barreira = threading.Barrier(4)

    def tablet():
        c = conectar(caminho)
        try:
            barreira.wait()
            comandas.abrir_mesa(c, 7, garcom.id)
            resultados.append("abriu")
        except MesaOcupadaError:
            resultados.append("ocupada")
        finally:
            c.close()

    threads = [threading.Thread(target=tablet) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(resultados) == ["abriu", "ocupada", "ocupada", "ocupada"]


def test_lancar_com_chave_nao_duplica_toque_repetido(conexao, operador, caixa_aberto):
    """O tablet reenvia o mesmo toque (rede instável): o item entra uma vez só."""
    mesa = comandas.abrir_mesa(conexao, 1, operador.id)
    primeiro = comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id, chave="toque-1")
    de_novo = comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id, chave="toque-1")
    assert not primeiro.repetido and de_novo.repetido and de_novo.item.id == primeiro.item.id
    comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id, chave="toque-2")  # outro toque conta
    assert comandas.calcular_conta(conexao, mesa.id).subtotal_centavos == 2 * 800
    outra = comandas.abrir_mesa(conexao, 2, operador.id)
    with pytest.raises(DadosInvalidosError):
        comandas.lancar_item(conexao, outra.id, BRAHMA, operador.id, chave="toque-1")
    assert comandas.calcular_conta(conexao, outra.id).subtotal_centavos == 0


def test_repetir_item_e_agrupar(conexao, operador, caixa_aberto):
    mesa = comandas.abrir_mesa(conexao, 1, operador.id)
    brahma = comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id).item
    comandas.lancar_item(conexao, mesa.id, CALABRESA, operador.id, observacao="bem passada")
    comandas.repetir_item(conexao, brahma.id, operador.id)  # "+" na linha da Brahma
    ultimo = comandas.repetir_item(conexao, brahma.id, operador.id, chave="mais-1").item
    comandas.repetir_item(conexao, brahma.id, operador.id, chave="mais-1")  # toque repetido
    grupos = comandas.agrupar_itens(comandas.listar_itens(conexao, mesa.id))
    assert [(g.nome_produto, g.quantidade, g.subtotal_centavos) for g in grupos] == [
        ("Brahma Lata", 3, 2400), ("Porção Calabresa", 1, 2800)]
    assert grupos[0].ultimo_item_id == ultimo.id  # o "−" tira do lançamento mais recente
    assert comandas.obter_resumo(conexao, mesa.id).quantidade_itens == 4
    # Observação diferente vira outra linha; trocar a observação da linha muda todos os lançamentos dela.
    comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id, observacao="sem gelo")
    assert len(comandas.agrupar_itens(comandas.listar_itens(conexao, mesa.id))) == 3
    comandas.alterar_observacao_grupo(conexao, brahma.id, "sem gelo", operador.id)
    grupos = comandas.agrupar_itens(comandas.listar_itens(conexao, mesa.id))
    assert [(g.nome_produto, g.observacao, g.quantidade) for g in grupos] == [
        ("Brahma Lata", "sem gelo", 4), ("Porção Calabresa", "bem passada", 1)]
    assert comandas.calcular_conta(conexao, mesa.id).subtotal_centavos == 4 * 800 + 2800


def test_remover_item_ja_retirado_em_outro_aparelho(conexao, operador, caixa_aberto):
    mesa = comandas.abrir_mesa(conexao, 1, operador.id)
    item = comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id).item
    comandas.remover_item(conexao, item.id, operador.id)
    with pytest.raises(DadosInvalidosError, match="já foi retirado"):
        comandas.remover_item(conexao, item.id, operador.id)
