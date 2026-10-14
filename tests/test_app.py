import pytest

import config
from app import ambiente_para, create_app, preparar_dados
from services.backup import listar_backups


@pytest.fixture
def app(tmp_path):
    return create_app(pasta_dados=tmp_path, ambiente="desenvolvimento")


def test_pagina_inicial(app):
    resposta = app.test_client().get("/")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Tucandeira Rock Bar" in html
    assert 'lang="pt-BR"' in html
    assert "/static/css/estilo.css" in html
    assert "/static/img/logo-" in html


def test_arquivos_estaticos(app):
    cliente = app.test_client()
    for caminho in ["/static/css/estilo.css", "/static/fonts/Anton-Regular.woff2",
                    "/static/fonts/Anton-Regular.ttf", "/static/img/logo-56.png"]:
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200, caminho
        resposta.close()


def test_css_carrega_anton_local(app):
    resposta = app.test_client().get("/static/css/estilo.css")
    css = resposta.get_data(as_text=True)
    resposta.close()
    assert "@font-face" in css and "../fonts/Anton-Regular.woff2" in css
    assert "fonts.googleapis" not in css


def test_filtro_moeda(app):
    with app.app_context():
        assert app.jinja_env.from_string("{{ 123456 | moeda }}").render() == "R$ 1.234,56"


def test_primeira_inicializacao_sem_backup_depois_com_backup(tmp_path):
    _, backup, _ = preparar_dados(tmp_path, "desenvolvimento")
    assert backup is None
    assert (tmp_path / config.NOME_BANCO).exists()
    _, backup, _ = preparar_dados(tmp_path, "desenvolvimento")
    assert backup is not None and backup.exists()
    assert len(listar_backups(tmp_path / config.NOME_PASTA_BACKUPS)) == 1


def test_ambiente_so_e_desenvolvimento_na_pasta_data_do_projeto(tmp_path):
    assert ambiente_para(config.PASTA_DADOS_DESENVOLVIMENTO) == "desenvolvimento"
    assert ambiente_para(tmp_path) == "producao"
